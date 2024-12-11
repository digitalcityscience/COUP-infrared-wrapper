import geopandas as gpd
import pyvista as pv
import shapely
from dotbimpy import *
import uuid

path_buildings = 'infrared_wrapper_api/models/jsons/buildings_multiple_bboxes.json'

gdf = gpd.read_file(path_buildings)
gdf = gdf.to_crs('EPSG:25832')
centroid = gdf['geometry'].union_all().centroid
centroid = shapely.get_coordinates(centroid).tolist()[0]
c_x = centroid[0]
c_y = centroid[1]
meshes = []
elements = []

counter = 0
for _, row in gdf.iterrows():
    geometry = row['geometry']
    height = row['building_height']

    # Skip invalid or empty geometries
    if geometry.is_empty or not geometry.is_valid:
        print("Skipping invalid or empty geometry")
        continue

    # Fix precision issues and check area
    geometry = geometry.buffer(0)
    if geometry.area == 0 or len(geometry.exterior.coords) < 3:
        print("Skipping degenerate or zero-area geometry")
        continue

    # Remove duplicate closing point
    exterior = [(x-c_x, y-c_y, 0) for x, y in geometry.exterior.coords]
    if exterior[0] == exterior[-1]:
        exterior = exterior[:-1]

    # Check bounds to skip degenerate polygons
    x_coords, y_coords = zip(*[(x, y) for x, y, _ in exterior])
    if max(x_coords) - min(x_coords) == 0 or max(y_coords) - min(y_coords) == 0:
        print("Degenerate geometry: all points lie on a line or single point")
        continue    

    # Create and triangulate PolyData
    base_polygon = pv.PolyData(exterior).delaunay_2d()
    
    extrusion = base_polygon.extrude([0, 0, height], capping=True)
    extrusion = extrusion.triangulate()
    

    extrusion = extrusion.extract_surface()
    coordinates = extrusion.points.flatten().tolist()
    indices = extrusion.regular_faces.flatten().tolist()

    vector = Vector(x=0,y=0,z=0)
    rotation = Rotation(qx=0, qy=0, qz=0, qw=1.0)
    geomtype = 'Block'
    color = Color(r=120, g=166, b=171, a=180)
    info = {'Name':f'building-{counter}'}
    guid = str(uuid.uuid4())

    mesh = Mesh(mesh_id=counter,coordinates=coordinates,indices=indices)
    element = Element(mesh_id=counter,vector=vector,rotation=rotation,guid=guid,type=geomtype,color=color,info=info)
    meshes.append(mesh)
    elements.append(element)
    counter=counter+1

file_info = {
    "Author":"DCS"
}

file = File("1.0.0",meshes=meshes,elements=elements,info=file_info)
file.save("buildings.bim")

