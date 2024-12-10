import pandas as pd
import geopandas as gpd
import pyvista as pv
import json
import shapely
import simplekml

path_buildings = 'infrared_wrapper_api/models/jsons/buildings_multiple_bboxes.json'

gdf = gpd.read_file(path_buildings)
gdf = gdf.to_crs('EPSG:25832')
centroid = gdf['geometry'].union_all().centroid
centroid = shapely.get_coordinates(centroid).tolist()[0]
c_x = centroid[0]
c_y = centroid[1]
print(centroid)

plotter = pv.Plotter()
combined_mesh = pv.MultiBlock()

from shapely.geometry import Polygon, MultiPolygon

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
    combined_mesh.append(extrusion)
    plotter.add_mesh(extrusion, color="white", opacity=0.8)
unified_mesh = combined_mesh.combine()

print(unified_mesh)

unified_mesh().save("buildings.vtk")
plotter.show()