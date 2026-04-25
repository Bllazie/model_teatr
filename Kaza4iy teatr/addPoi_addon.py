import bpy
import json
import csv
import os
from bpy_extras import view3d_utils

bl_info = {
    "name": "POI Manager Pro",
    "author": "Сивов Иван",
    "version": (2.1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > POI",
    "description": "Менеджер точек интереса для театральных моделей с экспортом JSON/CSV/TXT",
    "category": "3D View",
}

def get_poi_objects():
    """Возвращает список всех объектов-POI в сцене"""
    return [obj for obj in bpy.data.objects if "is_poi" in obj]

class POI_OT_InteractivePlace(bpy.types.Operator):
    """Интерактивное размещение точки кликом"""
    bl_idname = "poi.interactive_place"
    bl_label = "Добавить кликом"
    
    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            region = context.region
            rv3d = context.region_data
            coord = (event.mouse_region_x, event.mouse_region_y)
            
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            
            depsgraph = context.evaluated_depsgraph_get()
            hit, loc, norm, idx, obj, mat = context.scene.ray_cast(depsgraph, ray_origin, view_vector)

            if hit:
                bpy.ops.object.empty_add(type='SPHERE', radius=0.15, location=loc)
                new_poi = context.active_object
                new_poi.name = f"POI_{context.scene.poi_default_type}"
                new_poi["is_poi"] = True
                new_poi.poi_type = context.scene.poi_default_type
                new_poi.show_in_front = True 
                
                context.area.tag_redraw()
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class POI_OT_Delete(bpy.types.Operator):
    """Удаление конкретной точки из сцены"""
    bl_idname = "poi.delete_point"
    bl_label = "Удалить точку"
    target_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.target_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {'FINISHED'}

class POI_OT_Export(bpy.types.Operator):
    """Экспорт точек в выбранный формат"""
    bl_idname = "poi.export"
    bl_label = "Экспорт"
    
    format: bpy.props.EnumProperty(items=[
        ('JSON', "JSON", "JavaScript Object Notation"),
        ('CSV', "CSV", "Comma Separated Values"),
        ('TXT', "TXT", "Простой текст")
    ])

    def execute(self, context):
        pois = get_poi_objects()
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Сначала сохрани файл .blend!")
            return {'CANCELLED'}
        
        base_path = bpy.path.abspath("//poi_data")
        
        if self.format == 'JSON':
            data = [{"name": o.name, "type": o.poi_type, "loc": list(o.location)} for o in pois]
            with open(base_path + ".json", 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        
        elif self.format == 'CSV':
            with open(base_path + ".csv", 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Type", "X", "Y", "Z"])
                for o in pois:
                    writer.writerow([o.name, o.poi_type, o.location.x, o.location.y, o.location.z])
        
        elif self.format == 'TXT':
            with open(base_path + ".txt", 'w', encoding='utf-8') as f:
                for o in pois:
                    f.write(f"{o.name} | {o.poi_type} | {o.location}\n")

        self.report({'INFO'}, f"Экспортировано в {self.format}")
        return {'FINISHED'}

class POI_OT_Import(bpy.types.Operator):
    """Импорт точек из JSON"""
    bl_idname = "poi.import_json"
    bl_label = "Импорт JSON"

    def execute(self, context):
        path = bpy.path.abspath("//poi_data.json")
        if not os.path.exists(path):
            self.report({'ERROR'}, "Файл poi_data.json не найден!")
            return {'CANCELLED'}
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                bpy.ops.object.empty_add(type='SPHERE', radius=0.15, location=item['loc'])
                obj = context.active_object
                obj.name = item['name']
                obj["is_poi"] = True
                obj.poi_type = item['type']
        
        return {'FINISHED'}



class POI_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.label(text="", icon='EMPTY_DATA')
        row.prop(item, "name", text="", emboss=False)
        row.prop(item, "poi_type", text="")
        
        op = row.operator("poi.delete_point", text="", icon='X', emboss=False)
        op.target_name = item.name

    def filter_items(self, context, data, propname):
        objects = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item if "is_poi" in obj else 0 for obj in objects]
        flt_neworder = bpy.types.UI_UL_list.sort_items_by_name(objects, "name")
        return flt_flags, flt_neworder

class POI_PT_MainPanel(bpy.types.Panel):
    bl_label = "POI Manager Pro"
    bl_idname = "POI_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'POI'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "poi_default_type", text="Тип")
        layout.operator("poi.interactive_place", icon='MOUSE_LMB')
        
        layout.separator()
        layout.template_list("POI_UL_List", "", bpy.data, "objects", scene, "poi_idx")
        
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Экспорт данных:")
        row = col.row(align=True)
        row.operator("poi.export", text="JSON").format = 'JSON'
        row.operator("poi.export", text="CSV").format = 'CSV'
        row.operator("poi.export", text="TXT").format = 'TXT'
        
        layout.operator("poi.import_json", icon='IMPORT')

classes = [
    POI_OT_InteractivePlace, 
    POI_OT_Delete, 
    POI_OT_Export, 
    POI_OT_Import, 
    POI_UL_List, 
    POI_PT_MainPanel
]

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.poi_idx = bpy.props.IntProperty()
    types = [('DECOR', "Лепнина", ""), ('INFO', "Инфо", ""), ('DOOR', "Вход", "")]
    bpy.types.Scene.poi_default_type = bpy.props.EnumProperty(items=types, default='DECOR')
    bpy.types.Object.poi_type = bpy.props.EnumProperty(items=types)

def unregister():
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    del bpy.types.Scene.poi_idx
    del bpy.types.Scene.poi_default_type
    del bpy.types.Object.poi_type

if __name__ == "__main__":
    register()