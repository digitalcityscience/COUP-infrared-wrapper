import geopandas as gpd
import json
import uuid
import shapely
import pyvista as pv
import geopandas as gpd
import gzip, zipfile, base64
import base64
import io


# gets a values from a nested object
def get_value(data, path):
    for prop in path:
        if len(prop) == 0:
            continue
        if prop.isdigit():
            prop = int(prop)
        data = data[prop]
    return data


def reproject_geojson(geojson_in: dict, source_crs, target_crs) -> dict:
    gdf = gpd.GeoDataFrame.from_features(geojson_in)
    gdf = gdf.set_crs(source_crs, allow_override=True)

    return json.loads(gdf.to_crs(target_crs).to_json())

# function to extrude 2D geojsons and create meshes to match infrared's API
def transform_to_bim(gdf: gpd.GeoDataFrame):
    """
    extrudes a 2D geodataframe and creates 3D (.bim-based) objects for simulation with the infrared api

    Parameters:
        gdf (gpd.GeoDataFrame): Input GeoDataFrame with Polygons or Multipolygons, 'building_height' attribute required for calculation

    Returns:
        dict: A dictionary containing BIM geometry data keyed by unique GUIDs.
    """
    # Filter out rows with missing building heights and convert CRS
    gdf = gdf.loc[~gdf['building_height'].isna()]
    gdf = gdf.explode()
    gdf = gdf.to_crs('EPSG:25832')

    # Calculate the centroid of all geometries
    centroid = gdf['geometry'].unary_union.centroid
    c_x, c_y = shapely.get_coordinates(centroid).tolist()[0]

    geometries = {}
    counter = 0

    for _, row in gdf.iterrows():
        geometry = row['geometry']
        height = row['building_height']

        # Skip invalid or empty geometries
        if not geometry.is_valid or geometry.is_empty:
            print("Skipping invalid or empty geometry")
            continue

        # Fix precision issues and check for valid area
        geometry = geometry.buffer(0)
        if geometry.area == 0 or len(geometry.exterior.coords) < 3:
            print("Skipping degenerate or zero-area geometry")
            continue

        # Adjust coordinates relative to centroid and remove duplicate closing point
        exterior = [(x - c_x, y - c_y, 0) for x, y in geometry.exterior.coords[:-1]]

        # Ensure geometry is not degenerate (e.g., all points in a line)
        x_coords, y_coords = zip(*[(x, y) for x, y, _ in exterior])
        if max(x_coords) - min(x_coords) == 0 or max(y_coords) - min(y_coords) == 0:
            print("Degenerate geometry: all points lie on a line or single point")
            continue

        # Create base polygon and perform 2D triangulation
        try:
            base_polygon = pv.PolyData(exterior).delaunay_2d()
        except Exception as e:
            print(f"Error in triangulation: {e}")
            continue

        # Extrude the polygon to create 3D geometry
        extrusion = base_polygon.extrude([0, 0, height], capping=True).triangulate().extract_surface()

        # Collect mesh data
        coordinates = extrusion.points.flatten().tolist()
        indices = extrusion.faces.reshape(-1, 4)[:, 1:].flatten().tolist()  # Skip the face counts
        guid = str(uuid.uuid4())

        geometries[guid] = {
            "mesh_id": counter,
            "coordinates": coordinates,
            "indices": indices
        }

        counter += 1

    return geometries


def decompress_base64(compressed_base64):
    """
    Decompress a base64 encoded string that might be compressed with ZIP or GZIP.
    
    Args:
        compressed_base64 (str): Base64 encoded compressed data
    
    Returns:
        bytes: Decompressed data
    """
    # Decode base64 to bytes
    compressed_bytes = base64.b64decode(compressed_base64)
    
    # Try ZIP first
    try:
        with io.BytesIO(compressed_bytes) as compressed_io:
            with zipfile.ZipFile(compressed_io, 'r') as zf:
                # Get the first file in the archive
                if zf.namelist():
                    file_name = zf.namelist()[0]
                    with zf.open(file_name) as file:
                        return file.read().decode('utf-8')
    except zipfile.BadZipFile:
        # If not a ZIP file, try GZIP
        try:
            with io.BytesIO(compressed_bytes) as compressed_io:
                with gzip.GzipFile(fileobj=compressed_io, mode='rb') as gz:
                    return gz.read().decode('utf-8')
        except gzip.BadGzipFile:
            # If neither ZIP nor GZIP works, raise an error
            raise ValueError("Could not decompress the base64 string. Unknown compression format.")
