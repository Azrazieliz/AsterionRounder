"""Headless Blender viewport renderer. Invoked by File Gestioner's PC bridge.
Launch: blender --background --factory-startup --python fg_blender_frame.py -- KIND SOURCE OUTPUT YAW PITCH DISTANCE
No editing or saving of source .blend files.
"""
import sys,math,pathlib,traceback
argv=sys.argv[sys.argv.index("--")+1:]
kind,source,target=argv[:3]
yaw,pitch,distance=map(float,argv[3:6])
import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
if kind=="blend":
    path=pathlib.Path(source).resolve(strict=True)
    if path.suffix.lower() not in (".blend",".blend1"):
        raise ValueError("Only Blender source files are accepted here")
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False)
elif kind=="cube":
    bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,0))
    obj=bpy.context.object
    mat=bpy.data.materials.new(name="File Gestioner Cube")
    mat.diffuse_color=(0.26,0.52,0.92,1)
    obj.data.materials.append(mat)
else: raise ValueError("Unsupported Blender session")
meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
if not meshes:
    raise RuntimeError("Scene contains no renderable meshes")
points=[]
for obj in meshes:
    for corner in obj.bound_box:
        points.append(obj.matrix_world @ Vector(corner))
center=sum(points,Vector((0,0,0)))/len(points)
extent=max(max((p-center).length for p in points),0.1)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE"
scene.render.resolution_x=680
scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="JPEG"
scene.render.image_settings.quality=78
scene.render.filepath=str(pathlib.Path(target).resolve())
scene.render.film_transparent=False
scene.world=bpy.data.worlds.new("FG Background")
scene.world.use_nodes=True
scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value=(0.055,0.075,0.11,1)
scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value=0.65
pitch=max(-1.35,min(1.35,pitch))
distance=max(1.05,min(15,distance))*extent*2.0
direction=Vector((math.cos(pitch)*math.sin(yaw),-math.cos(pitch)*math.cos(yaw),math.sin(pitch)))
bpy.ops.object.camera_add(location=center+direction*distance)
camera=bpy.context.object
camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="PERSP"
camera.data.lens=38
scene.camera=camera
for name,loc,power,size in (
    ("Key",Vector((3,-4,7)),1200,5),
    ("Fill",Vector((-3,1,3)),750,4),
):
    bpy.ops.object.light_add(type="AREA",location=center+loc*max(1,extent))
    lamp=bpy.context.object
    lamp.name=name
    lamp.data.energy=power*max(1,extent)
    lamp.data.shape="DISK"
    lamp.data.size=size*max(1,extent)
    lamp.rotation_euler=(center-lamp.location).to_track_quat("-Z","Y").to_euler()
scene.view_settings.view_transform="AgX"
bpy.ops.render.render(write_still=True)
output=pathlib.Path(target)
if not output.is_file() or output.stat().st_size<100:
    raise RuntimeError("Blender rendered no frame")
print("FG_BLENDER_RENDER_OK",str(output),output.stat().st_size,flush=True)
