bl_info = {
    "name": "Advanced Inner Shell Generator",
    "author": "Lain",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > LainTool Tab",
    "description": "多算法集成补内面插件，强制UI显示修正版",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector

# -------------------------------------------------------------------
# 1. 属性组定义 (存储UI参数)
# -------------------------------------------------------------------
class InnerShellProperties(bpy.types.PropertyGroup):
    thickness: bpy.props.FloatProperty(
        name="厚度", 
        default=0.1, 
        min=0.0, 
        precision=3,
        description="向内生成的厚度距离"
    )
    algorithm: bpy.props.EnumProperty(
        name="算法",
        items=[
            ('SIMPLE', "基础偏移", "简单法线挤出"),
            ('SMOOTH', "优化平滑", "带平滑的优化算法，减少面重叠")
        ],
        default='SMOOTH'
    )
    iterations: bpy.props.IntProperty(
        name="优化迭代", 
        default=3, 
        min=1, 
        max=10,
        description="平滑算法的计算次数"
    )

# -------------------------------------------------------------------
# 2. 核心操作符 (执行逻辑)
# -------------------------------------------------------------------
class MESH_OT_generate_inner_shell(bpy.types.Operator):
    bl_idname = "mesh.generate_inner_shell"
    bl_label = "执行生成内面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 确保只在编辑模式且选中网格时可用
        return context.active_object is not None and \
               context.active_object.type == 'MESH' and \
               context.active_object.mode == 'EDIT'

    def execute(self, context):
        props = context.scene.inner_shell_props
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # 获取选中的面
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "未选中任何面，请先选择要操作的区域")
            return {'CANCELLED'}

        # A. 复制几何体
        ret = bmesh.ops.duplicate(bm, geom=selected_faces)
        new_geom = ret["geom"]
        new_faces = [f for f in new_geom if isinstance(f, bmesh.types.BMFace)]
        new_verts = list(set(v for f in new_faces for v in f.verts))

        # B. 算法应用
        if props.algorithm == 'SIMPLE':
            for v in new_verts:
                v.co -= v.normal * props.thickness
        else:
            # 初始偏移
            for v in new_verts:
                v.co -= v.normal * props.thickness
            # 拉普拉斯平滑优化
            for _ in range(props.iterations):
                for v in new_verts:
                    if not v.link_edges: continue
                    neighbor_avg = sum((e.other_vert(v).co for e in v.link_edges), Vector((0,0,0))) / len(v.link_edges)
                    v.co = v.co.lerp(neighbor_avg, 0.4)

        # C. 法线反转（核心步骤：让新生成的面朝里）
        bmesh.ops.reverse_faces(bm, faces=new_faces)

        # 刷新并退出
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "内面生成成功")
        return {'FINISHED'}

# -------------------------------------------------------------------
# 3. UI 面板定义
# -------------------------------------------------------------------
class VIEW3D_PT_inner_shell_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LainTool'  # 修改标签页名称，确保不被掩盖
    bl_label = "内面生成助手"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.inner_shell_props

        # 布局绘制
        box = layout.box()
        col = box.column(align=True)
        col.label(text="参数调节:", icon='SETTINGS')
        col.prop(props, "thickness")
        col.prop(props, "algorithm")
        
        if props.algorithm == 'SMOOTH':
            col.prop(props, "iterations")
        
        layout.separator()
        
        # 绘制按钮
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mesh.generate_inner_shell", icon='MESH_ICOSPHERE')

# -------------------------------------------------------------------
# 4. 注册与反注册
# -------------------------------------------------------------------
classes = (
    InnerShellProperties,
    MESH_OT_generate_inner_shell,
    VIEW3D_PT_inner_shell_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 将属性挂载到场景中，必须在类注册之后
    bpy.types.Scene.inner_shell_props = bpy.props.PointerProperty(type=InnerShellProperties)

def unregister():
    # 清理顺序：先删属性引用，再反注册类
    if hasattr(bpy.types.Scene, "inner_shell_props"):
        del bpy.types.Scene.inner_shell_props
        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()