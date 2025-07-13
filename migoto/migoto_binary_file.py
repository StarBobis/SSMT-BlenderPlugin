
import numpy
import os

from ..utils.migoto_utils import MigotoUtils, Fatal
from dataclasses import dataclass, field, asdict
from ..utils.log_utils import LOG

@dataclass
class D3D11Element:
    SemanticName:str
    SemanticIndex:int
    Format:str
    ByteWidth:int
    # Which type of slot and slot number it use? eg:vb0
    ExtractSlot:str
    # Is it from pointlist or trianglelist or compute shader?
    ExtractTechnique:str
    # Human named category, also will be the buf file name suffix.
    Category:str

    # Fixed items
    InputSlot:str = field(default="0", init=False, repr=False)
    InputSlotClass:str = field(default="per-vertex", init=False, repr=False)
    InstanceDataStepRate:str = field(default="0", init=False, repr=False)

    # Generated Items
    ElementNumber:int = field(init=False,default=0)
    AlignedByteOffset:int
    ElementName:str = field(init=False,default="")

    def __post_init__(self):
        self.ElementName = self.get_indexed_semantic_name()

    def get_indexed_semantic_name(self)->str:
        if self.SemanticIndex == 0:
            return self.SemanticName
        else:
            return self.SemanticName + str(self.SemanticIndex)

class FMTFile:
    def __init__(self, fmt_file_path:str):
        self.stride = 0
        self.topology = ""
        self.format = ""
        self.gametypename = ""
        self.prefix = ""
        self.scale = "1.0"
        self.rotate_angle:bool = False
        self.rotate_angle_x:float = 0
        self.rotate_angle_y:float = 0
        self.rotate_angle_z:float = 0
        self.flip_winding:bool = False
        self.flip_mirror:bool = False
        self.flip_face_orientation:bool = False

        self.elements:list[D3D11Element] = []

        with open(fmt_file_path, 'r') as file:
            lines = file.readlines()

        element_info = {}
        for line in lines:
            parts = line.strip().split(":")
            if len(parts) < 2:
                continue  # 跳过格式不正确的行

            key, value = parts[0].strip(), ":".join(parts[1:]).strip()
            if key == "stride":
                self.stride = int(value)
            elif key == "topology":
                self.topology = value
            elif key == "format":
                self.format = value
            elif key == "gametypename":
                self.gametypename = value
            elif key == "prefix":
                self.prefix = value
            elif key == "scale":
                self.scale = value
            elif key == "rotate_angle":
                self.rotate_angle = value.lower() == "true"
            elif key == "rotate_angle_x":
                self.rotate_angle_x = float(value)
            elif key == "rotate_angle_y":
                self.rotate_angle_y = float(value)
            elif key == "rotate_angle_z":
                self.rotate_angle_z = float(value)
            
            elif key == "flip_winding":
                self.flip_winding = value.lower() == "true"
                
            elif key == "flip_mirror":
                self.flip_mirror = value.lower() == "true"
            
            elif key == "flip_face_orientation":
                self.flip_face_orientation = value.lower() == "true"

            elif key.startswith("element"):
                # 处理element块
                if "SemanticName" in element_info:
                    # 如果已经有一个element信息，则先添加到列表中
                    self.elements.append(D3D11Element(
                          SemanticName=element_info["SemanticName"], SemanticIndex=int(element_info["SemanticIndex"]),
                    Format= element_info["Format"],AlignedByteOffset= int(element_info["AlignedByteOffset"]),
                    ByteWidth=MigotoUtils.format_size(element_info["Format"]),
                    ExtractSlot="0",ExtractTechnique="",Category=""
                    ))
                    element_info.clear()  # 清空当前element信息

                # 将新的element属性添加到element_info字典中
                element_info[key.split()[0]] = value
            elif key in ["SemanticName", "SemanticIndex", "Format", "InputSlot", "AlignedByteOffset", "InputSlotClass", "InstanceDataStepRate"]:
                element_info[key] = value

        # 添加最后一个element
        if "SemanticName" in element_info:
            self.elements.append(D3D11Element(
                    SemanticName=element_info["SemanticName"], SemanticIndex=int(element_info["SemanticIndex"]),
                    Format= element_info["Format"],AlignedByteOffset= int(element_info["AlignedByteOffset"]),
                    ByteWidth=MigotoUtils.format_size(element_info["Format"]),
                    ExtractSlot="0",ExtractTechnique="",Category=""
            ))

    def __repr__(self):
        return (f"FMTFile(stride={self.stride}, topology='{self.topology}', format='{self.format}', "
                f"gametypename='{self.gametypename}', prefix='{self.prefix}', elements={self.elements})")
    
    def get_dtype(self):
        fields = []
        for elemnt in self.elements:
            # print("element: "+ elemnt.ElementName)
            numpy_type = MigotoUtils.get_nptype_from_format(elemnt.Format)
            size = MigotoUtils.format_components(elemnt.Format)

            # print(numpy_type)
            # print(size)

            fields.append((elemnt.ElementName,numpy_type , size))
        dtype = numpy.dtype(fields)
        return dtype
    


class MigotoBinaryFile:

    '''
    3Dmigoto模型文件

    暂时还没有更好的设计，暂时先沿用旧的ib vb fmt设计
    
    prefix是前缀，比如Body.ib Body.vb Body.fmt 那么此时Body就是prefix
    location_folder_path是存放这些文件的文件夹路径，比如当前工作空间中提取的对应数据类型文件夹

    '''
    def __init__(self, fmt_path:str, mesh_name:str = ""):
        self.fmt_file = FMTFile(fmt_path)
        print("fmt_path: " + fmt_path)
        location_folder_path = os.path.dirname(fmt_path)
        print("location_folder_path: " + location_folder_path)

        if self.fmt_file.prefix == "":
            self.fmt_file.prefix = os.path.basename(fmt_path).split(".fmt")[0]

        if mesh_name == "":
            self.mesh_name = self.fmt_file.prefix
        else:
            self.mesh_name = mesh_name
        

        print("prefix: " + self.fmt_file.prefix)
        self.init_from_prefix(self.fmt_file.prefix, location_folder_path)

    def init_from_prefix(self,prefix:str, location_folder_path:str):

        self.fmt_name = prefix + ".fmt"
        self.vb_name = prefix + ".vb"
        self.ib_name = prefix + ".ib"

        self.location_folder_path = location_folder_path

        self.vb_bin_path = os.path.join(location_folder_path, self.vb_name)
        self.ib_bin_path = os.path.join(location_folder_path, self.ib_name)
        self.fmt_path = os.path.join(location_folder_path, self.fmt_name)

        self.file_sanity_check()

        self.vb_file_size = os.path.getsize(self.vb_bin_path)
        self.ib_file_size = os.path.getsize(self.ib_bin_path)

        self.init_data()

    def init_data(self):
        ib_stride = MigotoUtils.format_size(self.fmt_file.format)

        self.ib_count = int(self.ib_file_size / ib_stride)
        self.ib_polygon_count = int(self.ib_count / 3)
        self.ib_data = numpy.fromfile(self.ib_bin_path, dtype=MigotoUtils.get_nptype_from_format(self.fmt_file.format), count=self.ib_count)
        
        # 读取fmt文件，解析出后面要用的dtype
        fmt_dtype = self.fmt_file.get_dtype()
        vb_stride = fmt_dtype.itemsize

        self.vb_vertex_count = int(self.vb_file_size / vb_stride)
        self.vb_data = numpy.fromfile(self.vb_bin_path, dtype=fmt_dtype, count=self.vb_vertex_count)

    
    def file_sanity_check(self):
        '''
        检查对应文件是否存在，不存在则抛出异常
        三个文件，必须都存在，缺一不可
        '''
        if not os.path.exists(self.vb_bin_path):
            raise Fatal("Unable to find matching .vb file for : " + self.mesh_name)
        if not os.path.exists(self.ib_bin_path):
            raise Fatal("Unable to find matching .ib file for : " + self.mesh_name)
        # if not os.path.exists(self.fmt_path):
        #     raise Fatal("Unable to find matching .fmt file for : " + self.mesh_name)

    def file_size_check(self) -> bool:
        '''
        检查.ib和.vb文件是否为空，如果为空则弹出错误提醒信息，但不报错。
        '''
        # 如果vb和ib文件不存在，则跳过导入
        # 我们不能直接抛出异常，因为有些.ib文件是空的占位文件
        if self.vb_file_size == 0:
            LOG.warning("Current Import " + self.vb_name +" file is empty, skip import.")
            return False
        
        if self.ib_file_size == 0:
            LOG.warning("Current Import " + self.ib_name + " file is empty, skip import.")
            return False
        
        return True