bl_info = {
    "name": "POI Manager (Basic)",
    "author": "Твоё имя",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > POI",
    "description": "Добавление точек интереса (POI) в сцену",
    "category": "3D View",
}

import bpy

# --- Оператор для добавления точки ---
class POI_OT_Add(bpy.types.Operator):
    """Добавить точку интереса"""
    bl_idname = "poi.add_point"
    bl_label = "Добавить POI"

    def execute(self, context):
        # создаём Empty (точку интереса)
        bpy.ops.object.add(type='EMPTY')
        obj = context.active_object
        obj.name = f"POI_{len([o for o in bpy.data.objects if 'POI_' in o.name])}"
        obj.empty_display_type = 'SPHERE'
        obj.empty_display_size = 0.2
        return {'FINISHED'}


# --- Панель интерфейса ---
class POI_PT_MainPanel(bpy.types.Panel):
    bl_label = "POI Manager"
    bl_idname = "POI_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'POI'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Точки интереса:")
        layout.operator("poi.add_point", icon='EMPTY_DATA')


# --- Регистрация ---
classes = [POI_OT_Add, POI_PT_MainPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
