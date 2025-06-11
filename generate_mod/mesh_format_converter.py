import math
import numpy

from ..properties.properties_generate_mod import Properties_GenerateMod
from ..utils.timer_utils import TimerUtils
from ..utils.log_utils import LOG

class MeshFormatConverter:
    '''
    用于各种二进制数据格式转换
    '''
    # 向量归一化
    @classmethod
    def vector_normalize(cls,v):
        """归一化向量"""
        length = math.sqrt(sum(x * x for x in v))
        if length == 0:
            return v  # 避免除以零
        return [x / length for x in v]
    
    @classmethod
    def add_and_normalize_vectors(cls,v1, v2):
        """将两个向量相加并规范化(normalize)"""
        # 相加
        result = [a + b for a, b in zip(v1, v2)]
        # 归一化
        normalized_result = cls.vector_normalize(result)
        return normalized_result
    
    # 辅助函数：计算两个向量的点积
    @classmethod
    def dot_product(cls,v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    '''
    这四个UNORM和SNORM比较特殊需要这样处理，其它float类型转换直接astype就行
    '''
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_snorm(cls, input_array):
        return numpy.round(input_array * 127).astype(numpy.int8)
    
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_unorm(cls,input_array):
        return numpy.round(input_array * 255).astype(numpy.uint8)
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_snorm(cls,input_array):
        return numpy.round(input_array * 32767).astype(numpy.int16)
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_unorm(cls, input_array):
        return numpy.round(input_array * 65535).astype(numpy.uint16)
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_snorm(cls, input_array):
        return numpy.round(input_array * 32767).astype(numpy.int16)
    
    @classmethod
    def average_normal_tangent(cls,obj,indexed_vertices,d3d11GameType,dtype):
        '''
        Nico: 米游所有游戏都能用到这个，还有曾经的GPU-PreSkinning的GF2也会用到这个，崩坏三2.0新角色除外。
        尽管这个可以起到相似的效果，但是仍然无法完美获取模型本身的TANGENT数据，只能做到身体轮廓线99%近似。
        经过测试，头发轮廓线部分并不是简单的向量归一化，也不是算术平均归一化。
        '''
        # TimerUtils.Start("Recalculate TANGENT")

        if "TANGENT" not in d3d11GameType.OrderedFullElementList:
            return indexed_vertices
        allow_calc = False
        if Properties_GenerateMod.recalculate_tangent():
            allow_calc = True
        elif obj.get("3DMigoto:RecalculateTANGENT",False): 
            allow_calc = True
        
        if not allow_calc:
            return indexed_vertices
        
        # 不用担心这个转换的效率，速度非常快
        vb = bytearray()
        for vertex in indexed_vertices:
            vb += bytes(vertex)
        vb = numpy.frombuffer(vb, dtype = dtype)

        # 开始重计算TANGENT
        positions = numpy.array([val['POSITION'] for val in vb])
        normals = numpy.array([val['NORMAL'] for val in vb], dtype=float)

        # 对位置进行排序，以便相同的位置会相邻
        sort_indices = numpy.lexsort(positions.T)
        sorted_positions = positions[sort_indices]
        sorted_normals = normals[sort_indices]

        # 找出位置变化的地方，即我们需要分组的地方
        group_indices = numpy.flatnonzero(numpy.any(sorted_positions[:-1] != sorted_positions[1:], axis=1))
        group_indices = numpy.r_[0, group_indices + 1, len(sorted_positions)]

        # 累加法线和计算计数
        unique_positions = sorted_positions[group_indices[:-1]]
        accumulated_normals = numpy.add.reduceat(sorted_normals, group_indices[:-1], axis=0)
        counts = numpy.diff(group_indices)

        # 归一化累积法线向量
        normalized_normals = accumulated_normals / numpy.linalg.norm(accumulated_normals, axis=1)[:, numpy.newaxis]
        normalized_normals[numpy.isnan(normalized_normals)] = 0  # 处理任何可能出现的零向量导致的除零错误

        # 构建结果字典
        position_normal_dict = dict(zip(map(tuple, unique_positions), normalized_normals))

        # TimerUtils.End("Recalculate TANGENT")

        # 获取所有位置并转换为元组，用于查找字典
        positions = [tuple(pos) for pos in vb['POSITION']]

        # 从字典中获取对应的标准化法线
        normalized_normals = numpy.array([position_normal_dict[pos] for pos in positions])

        # 计算 w 并调整 tangent 的第四个分量
        w = numpy.where(vb['TANGENT'][:, 3] >= 0, -1.0, 1.0)

        # 更新 TANGENT 分量，注意这里的切片操作假设 TANGENT 有四个分量
        vb['TANGENT'][:, :3] = normalized_normals
        vb['TANGENT'][:, 3] = w

        # TimerUtils.End("Recalculate TANGENT")

        return vb

    @classmethod
    def average_normal_color(cls,obj,indexed_vertices,d3d11GameType,dtype):
        '''
        Nico: 算数平均归一化法线，HI3 2.0角色使用的方法
        '''
        if "COLOR" not in d3d11GameType.OrderedFullElementList:
            return indexed_vertices
        allow_calc = False
        if Properties_GenerateMod.recalculate_color():
            allow_calc = True
        elif obj.get("3DMigoto:RecalculateCOLOR",False): 
            allow_calc = True
        if not allow_calc:
            return indexed_vertices

        # 开始重计算COLOR
        TimerUtils.Start("Recalculate COLOR")

        # 不用担心这个转换的效率，速度非常快
        vb = bytearray()
        for vertex in indexed_vertices:
            vb += bytes(vertex)
        vb = numpy.frombuffer(vb, dtype = dtype)

        # 首先提取所有唯一的位置，并创建一个索引映射
        unique_positions, position_indices = numpy.unique(
            [tuple(val['POSITION']) for val in vb], 
            return_inverse=True, 
            axis=0
        )

        # 初始化累积法线和计数器为零
        accumulated_normals = numpy.zeros((len(unique_positions), 3), dtype=float)
        counts = numpy.zeros(len(unique_positions), dtype=int)

        # 累加法线并增加计数（这里假设vb是一个list）
        for i, val in enumerate(vb):
            accumulated_normals[position_indices[i]] += numpy.array(val['NORMAL'], dtype=float)
            counts[position_indices[i]] += 1

        # 对所有位置的法线进行一次性规范化处理
        mask = counts > 0
        average_normals = numpy.zeros_like(accumulated_normals)
        average_normals[mask] = (accumulated_normals[mask] / counts[mask][:, None])

        # 归一化到[0,1]，然后映射到颜色值
        normalized_normals = ((average_normals + 1) / 2 * 255).astype(numpy.uint8)

        # 更新颜色信息
        new_color = []
        for i, val in enumerate(vb):
            color = [0, 0, 0, val['COLOR'][3]]  # 保留原来的Alpha通道
            
            if mask[position_indices[i]]:
                color[:3] = normalized_normals[position_indices[i]]

            new_color.append(color)

        # 将新的颜色列表转换为NumPy数组
        new_color_array = numpy.array(new_color, dtype=numpy.uint8)

        # 更新vb中的颜色信息
        for i, val in enumerate(vb):
            val['COLOR'] = new_color_array[i]

        TimerUtils.End("Recalculate COLOR")
        return vb



    @classmethod
    def convert_4x_float32_to_r8g8b8a8_unorm_blendweights(cls, input_array):
        TimerUtils.Start("convert_4x_float32_to_r8g8b8a8_unorm_blendweights")
        
        # 创建结果数组
        result = numpy.zeros_like(input_array, dtype=numpy.uint8)
        
        # 处理NaN值
        nan_mask = numpy.isnan(input_array).any(axis=1)
        valid_mask = ~nan_mask
        
        # 只处理非NaN行
        valid_input = input_array[valid_mask]
        if valid_input.size == 0:
            TimerUtils.End("convert_4x_float32_to_r8g8b8a8_unorm_blendweights")
            return result
        
        # 计算每行总和
        row_sums = valid_input.sum(axis=1, keepdims=True)
        
        # 处理零和行
        zero_sum_mask = (row_sums[:, 0] == 0)
        non_zero_mask = ~zero_sum_mask
        
        # 归一化权重
        normalized = numpy.zeros_like(valid_input)
        normalized[non_zero_mask] = valid_input[non_zero_mask] / row_sums[non_zero_mask] * 255.0
        
        # 计算整数部分和小数部分
        int_part = numpy.floor(normalized).astype(numpy.int32)
        fractional = normalized - int_part
        
        # 设置小于1的权重为0
        small_weight_mask = (normalized < 1) & non_zero_mask[:, numpy.newaxis]
        int_part[small_weight_mask] = 0
        fractional[small_weight_mask] = 0
        
        # 计算精度误差
        precision_error = 255 - int_part.sum(axis=1)
        
        # 计算tickets
        tickets = numpy.zeros_like(normalized)
        with numpy.errstate(divide='ignore', invalid='ignore'):
            tickets[non_zero_mask] = numpy.where(
                (normalized[non_zero_mask] >= 1) & (fractional[non_zero_mask] > 0),
                255 * fractional[non_zero_mask] / normalized[non_zero_mask],
                0
            )
        
        # 分配精度误差
        output = int_part.copy()
        for i in range(precision_error.max()):
            # 找出需要分配的行
            need_allocation = (precision_error > 0)
            if not numpy.any(need_allocation):
                break
            
            # 找出当前行中ticket最大的位置
            max_ticket_mask = numpy.zeros_like(tickets, dtype=bool)
            rows = numpy.where(need_allocation)[0]
            
            # 对于有ticket的行
            has_ticket = (tickets[rows] > 0).any(axis=1)
            if numpy.any(has_ticket):
                ticket_rows = rows[has_ticket]
                row_indices = ticket_rows[:, numpy.newaxis]
                col_indices = tickets[ticket_rows].argmax(axis=1)
                max_ticket_mask[ticket_rows, col_indices] = True
                tickets[ticket_rows, col_indices] = 0
            
            # 对于没有ticket的行
            no_ticket = ~has_ticket & need_allocation[rows]
            if numpy.any(no_ticket):
                no_ticket_rows = rows[no_ticket]
                # 找出当前权重最大的位置
                max_weight_mask = numpy.zeros_like(tickets, dtype=bool)
                row_indices = no_ticket_rows[:, numpy.newaxis]
                col_indices = output[no_ticket_rows].argmax(axis=1)
                max_weight_mask[no_ticket_rows, col_indices] = True
                max_ticket_mask |= max_weight_mask
            
            # 应用分配
            output[max_ticket_mask] += 1
            precision_error[need_allocation] -= 1
        
        # 将结果存回
        result[valid_mask] = output.astype(numpy.uint8)
        
        TimerUtils.End("convert_4x_float32_to_r8g8b8a8_unorm_blendweights")
        return result
    
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_unorm_blendweights_bk2(cls, input_array):
        TimerUtils.Start("convert_4x_float32_to_r8g8b8a8_unorm_blendweights")
        # print(f"Input shape: {input_array.shape}")  # 输出形状 (1896, 4)

        result = numpy.zeros_like(input_array, dtype=numpy.uint8)

        for i in range(input_array.shape[0]):
            weights = input_array[i]

            # 如果权重含有NaN值，则将该行的所有值设置为0。
            # 因为权重只要是被刷过，就不会出现NaN值。
            find_nan = False
            for w in weights:
                if math.isnan(w):
                    row_normalized = [0, 0, 0, 0]
                    result[i] = numpy.array(row_normalized, dtype=numpy.uint8)
                    find_nan = True
                    break
                    # print(weights)
                    # raise Fatal("NaN found in weights")
            if find_nan:
                continue
            
            total = sum(weights)
            if total == 0:
                row_normalized = [0] * len(weights)
                result[i] = numpy.array(row_normalized, dtype=numpy.uint8)
                continue

            precision_error = 255

            tickets = [0] * len(weights)
            normalized_weights = [0] * len(weights)

            for index, weight in enumerate(weights):
                # Ignore zero weight
                if weight == 0:
                    continue

                weight = weight / total * 255
                # Ignore weight below minimal precision (1/255)
                if weight < 1:
                    normalized_weights[index] = 0
                    continue

                # Strip float part from the weight
                int_weight = 0

                int_weight = int(weight)

                normalized_weights[index] = int_weight
                # Reduce precision_error by the integer weight value
                precision_error -= int_weight
                # Calculate weight 'significance' index to prioritize lower weights with float loss
                tickets[index] = 255 / weight * (weight - int_weight)

            while precision_error > 0:
                ticket = max(tickets)
                if ticket > 0:
                    # Route `1` from precision_error to weights with non-zero ticket value first
                    idx = tickets.index(ticket)
                    tickets[idx] = 0
                else:
                    # Route remaining precision_error to highest weight to reduce its impact
                    idx = normalized_weights.index(max(normalized_weights))
                # Distribute `1` from precision_error
                normalized_weights[idx] += 1
                precision_error -= 1

            row_normalized = normalized_weights
            result[i] = numpy.array(row_normalized, dtype=numpy.uint8)
        TimerUtils.End("convert_4x_float32_to_r8g8b8a8_unorm_blendweights")

        return result