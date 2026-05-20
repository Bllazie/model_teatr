import bpy
import json
import csv
import os
from bpy_extras import view3d_utils

bl_info = {
    "name": "POI Manager Pro",
    "author": "Сивов Иван",
    "version": (2, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > POI",
    "description": "Менеджер точек интереса для театральных моделей с экспортом JSON/CSV/TXT",
    "category": "3D View",
}

POI_COLLECTION_NAME = "POI"


def get_or_create_poi_collection():
    """Возвращает коллекцию POI, создавая её при необходимости."""
    col = bpy.data.collections.get(POI_COLLECTION_NAME)
    if col is None:
        col = bpy.data.collections.new(POI_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(col)
    return col


def get_poi_objects():
    """Возвращает список всех объектов-POI в сцене."""
    return [obj for obj in bpy.data.objects if "is_poi" in obj]


def link_to_poi_collection(obj):
    """Помещает объект в коллекцию POI, убирая из всех остальных коллекций."""
    poi_col = get_or_create_poi_collection()
        
    for col in list(obj.users_collection):
        col.objects.unlink(obj)

    poi_col.objects.link(obj)


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
            hit, loc, norm, idx, obj, mat = context.scene.ray_cast(
                depsgraph, ray_origin, view_vector
            )

            if hit:
                poi_type = context.scene.poi_default_type

                empty = bpy.data.objects.new(f"POI_{poi_type}", None)
                empty.empty_display_type = 'SPHERE'
                empty.empty_display_size = 0.15
                empty.location = loc
                empty["is_poi"] = True
                empty.poi_type = poi_type
                empty.show_in_front = True

                link_to_poi_collection(empty)

                context.area.tag_redraw()
                return {'FINISHED'}

            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Запусти из окна 3D Viewport")
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Кликни на модель. ПКМ / ESC — отмена")
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
        ('CSV',  "CSV",  "Comma Separated Values"),
        ('TXT',  "TXT",  "Простой текст"),
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
                empty = bpy.data.objects.new(item['name'], None)
                empty.empty_display_type = 'SPHERE'
                empty.empty_display_size = 0.15
                empty.location = item['loc']
                empty["is_poi"] = True
                empty.poi_type = item['type']

                link_to_poi_collection(empty)

        return {'FINISHED'}


class POI_OT_AutoGenerate(bpy.types.Operator):
    """Автоматический анализ сцены и расстановка важных точек (Топ-N)"""
    bl_idname = "poi.auto_generate"
    bl_label = "Авто-генерация POI"
    bl_options = {'REGISTER', 'UNDO'}

    min_polygons: bpy.props.IntProperty(
        name="Мин. полигонов",
        description="Отсекает простые формы (стены, стекла, кубы)",
        default=50,
        min=1,
    )
    min_volume: bpy.props.FloatProperty(
        name="Мин. объем (м³)",
        description="Отсекает микроскопические детали",
        default=0.01,
        min=0.0001,
    )
    max_pois: bpy.props.IntProperty(
        name="Лимит точек (Топ-N)",
        description="Сколько самых важных групп элементов выделить",
        default=10,
        min=1,
        max=50,
    )

    def execute(self, context):
        mesh_objects = [
            obj for obj in context.scene.objects
            if obj.type == 'MESH' and "is_poi" not in obj and obj.visible_get()
        ]

        if not mesh_objects:
            self.report({'WARNING'}, "В сцене нет подходящих 3D-моделей!")
            return {'CANCELLED'}

        def get_volume(o):
            d = o.dimensions
            return d[0] * d[1] * d[2]

        mesh_objects.sort(key=get_volume, reverse=True)
        main_building = mesh_objects[0]
        main_mesh_name = main_building.data.name

        self.create_poi(context, main_building, "Главное здание", 'INFO', 1, main_mesh_name)

        groups = {}
        for obj in mesh_objects[1:]:
            if obj.data.name == main_mesh_name:
                continue
            if get_volume(obj) < self.min_volume:
                continue
            try:
                poly_count = len(obj.data.polygons)
            except Exception:
                continue
            if poly_count < self.min_polygons:
                continue

            mesh_name = obj.data.name
            if mesh_name not in groups:
                groups[mesh_name] = {"objects": [], "poly_count": poly_count}
            groups[mesh_name]["objects"].append(obj)

        sorted_groups = sorted(
            groups.items(),
            key=lambda item: len(item[1]["objects"]) * item[1]["poly_count"],
            reverse=True,
        )

        created_count = 0
        for mesh_name, data in sorted_groups[: self.max_pois]:
            objects = data["objects"]
            target_obj = objects[0]
            count = len(objects)

            if count > 1:
                poi_type = 'DECOR'
                name = f"Массовый декор ({count} шт)"
            else:
                poi_type = 'INFO'
                name = "Уникальный элемент (1 шт)"

            self.create_poi(context, target_obj, name, poi_type, count, mesh_name)
            created_count += 1

        self.report({'INFO'}, f"Анализ завершен: выделено {created_count + 1} главных объектов.")
        return {'FINISHED'}

    def create_poi(self, context, target_obj, name, poi_type, count, target_mesh_name):
        """Вспомогательная функция для создания точки."""
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'SPHERE'
        empty.empty_display_size = 0.3
        empty.location = target_obj.location.copy()
        empty["is_poi"] = True
        empty.poi_type = poi_type
        empty.show_in_front = True
        empty["instance_count"] = count
        empty["target_mesh"] = target_mesh_name

        link_to_poi_collection(empty)


class POI_OT_SelectIdentical(bpy.types.Operator):
    """Выделяет на модели все детали, связанные с выбранной POI"""
    bl_idname = "poi.select_identical"
    bl_label = "Выделить все такие детали"

    target_mesh: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.scene.objects:
            obj.select_set(False)

        count = 0
        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.data.name == self.target_mesh:
                obj.select_set(True)
                count += 1

        if count > 0:
            context.view_layer.objects.active = context.selected_objects[0]
            self.report({'INFO'}, f"Выделено элементов на фасаде: {count}")
        else:
            self.report({'WARNING'}, "Элементы не найдены. Возможно, модель была изменена.")

        return {'FINISHED'}


class POI_UL_List(bpy.types.UIList):
    use_filter_sort_alpha = False

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.label(text="", icon='EMPTY_DATA')
        row.prop(item, "name", text="", emboss=False)
        row.prop(item, "poi_type", text="")

        if "instance_count" in item and item["instance_count"] > 1:
            row.label(text=f"x{item['instance_count']}")
            op_sel = row.operator("poi.select_identical", text="", icon='RESTRICT_SELECT_OFF', emboss=False)
            op_sel.target_mesh = item["target_mesh"]

        op = row.operator("poi.delete_point", text="", icon='X', emboss=False)
        op.target_name = item.name

    def filter_items(self, context, data, propname):
        objects = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item if "is_poi" in obj else 0 for obj in objects]

        if self.filter_name:
            search_flags = bpy.types.UI_UL_list.filter_items_by_name(
                self.filter_name, self.bitflag_filter_item, objects, propname="name"
            )
            for i, flag in enumerate(search_flags):
                if self.use_filter_invert:
                    if flag & self.bitflag_filter_item:
                        flt_flags[i] &= ~self.bitflag_filter_item
                else:
                    if not (flag & self.bitflag_filter_item):
                        flt_flags[i] &= ~self.bitflag_filter_item

        return flt_flags, []


class POI_PT_MainPanel(bpy.types.Panel):
    bl_label = "POI Manager Pro"
    bl_idname = "POI_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'POI'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator("poi.auto_generate", icon='OUTLINER_OB_LIGHTPROBE', text="Авто-анализ здания")
        layout.separator()

        layout.prop(scene, "poi_default_type", text="Тип")
        layout.operator("poi.interactive_place", icon='MOUSE_LMB', text="Добавить кликом (ЛКМ)")

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
    POI_PT_MainPanel,
    POI_OT_AutoGenerate,
    POI_OT_SelectIdentical,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.poi_idx = bpy.props.IntProperty()
    types = [
        ('DECOR', "Лепнина", ""),
        ('INFO',  "Инфо",    ""),
        ('DOOR',  "Вход",    ""),
    ]
    bpy.types.Scene.poi_default_type = bpy.props.EnumProperty(items=types, default='DECOR')
    bpy.types.Object.poi_type = bpy.props.EnumProperty(items=types)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.poi_idx
    del bpy.types.Scene.poi_default_type
    del bpy.types.Object.poi_type


if __name__ == "__main__":
    register()