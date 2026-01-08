bl_info = {
    "name": "POI Manager Pro",
    "author": "Сивов Иван",
    "version": (1, 2),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > POI",
    "description": "Управление точками интереса (POI) для Казачьего театра",
    "category": "3D View",
}

import bpy
import json
import os

class POI_OT_Add(bpy.types.Operator):
    bl_idname = "poi.add_point"
    bl_label = "Добавить POI"
    
    def execute(self, context):
        bpy.ops.object.empty_add(type='SPHERE', radius=0.2, location=context.scene.cursor.location)
        obj = context.active_object
        
        count = len([o for o in bpy.data.objects if "is_poi" in o])
        obj.name = f"POI_Point_{count + 1}"
        
        obj["is_poi"] = True
        context.area.tag_redraw()
        return {'FINISHED'}

class POI_OT_Delete(bpy.types.Operator):
    bl_idname = "poi.delete_point"
    bl_label = "Удалить"
    
    target_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.target_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {'FINISHED'}

class POI_OT_Export(bpy.types.Operator):
    bl_idname = "poi.export_json"
    bl_label = "Экспорт всех POI в JSON"
    
    def execute(self, context):
        poi_data = []
        for obj in bpy.data.objects:
            if "is_poi" in obj:
                poi_data.append({
                    "name": obj.name,
                    "location": {
                        "x": round(obj.location.x, 3),
                        "y": round(obj.location.y, 3),
                        "z": round(obj.location.z, 3)
                    }
                })
        
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Сначала сохрани .blend файл!")
            return {'CANCELLED'}

        filepath = bpy.path.abspath("//poi_list.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(poi_data, f, ensure_ascii=False, indent=4)
            
        self.report({'INFO'}, f"Экспортировано {len(poi_data)} точек в JSON")
        return {'FINISHED'}

class POI_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if "is_poi" in item:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon='EMPTY_DATA')
           
            op = row.operator("poi.delete_point", text="", icon='X')
            op.target_name = item.name

    def draw_filter(self, context, layout):
        pass

    def filter_items(self, context, data, propname):
        objects = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item if "is_poi" in obj else 0 for obj in objects]
        return flt_flags, []

class POI_PT_MainPanel(bpy.types.Panel):
    bl_label = "POI Manager (Казачий Театр)"
    bl_idname = "POI_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'POI'

    def draw(self, context):
        layout = self.layout
        
        layout.operator("poi.add_point", icon='ADD', text="Поставить точку (в курсор)")
        layout.separator()

        layout.label(text="Список активных точек:")
        layout.template_list("POI_UL_List", "", bpy.data, "objects", context.scene, "poi_idx")
        
        layout.separator()
        layout.operator("poi.export_json", icon='FILE_TICK')

classes = [POI_OT_Add, POI_OT_Delete, POI_OT_Export, POI_UL_List, POI_PT_MainPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.poi_idx = bpy.props.IntProperty()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.poi_idx

if __name__ == "__main__":
    register()