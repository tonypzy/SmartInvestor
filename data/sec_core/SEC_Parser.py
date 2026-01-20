import os
import glob
import re
import json
from lxml import etree
from dateutil import parser as date_parser

class SEC_Parser:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), 'metrics_config.json')
        try:
            with open(config_path, 'r') as f:
                self.metrics_map = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load metrics config: {e}")
            self.metrics_map = {}

    def parse_single_filing(self, path_input):
        target_file = None

        # 1. 智能路径搜索
        if os.path.isfile(path_input):
            target_file = path_input
        else:
            target_extensions = ["*.xml", "*.htm", "*.html"]
            files = []
            for ext in target_extensions:
                files.extend(glob.glob(os.path.join(path_input, "**", ext), recursive=True))
            if files:
                target_file = max(files, key=os.path.getsize)

        if not target_file:
            print(f"⚠️ [Parser] No XML/HTML file found in: {path_input}")
            return None
        
        extracted_data = {'Source': 'Unknown', 'File': os.path.basename(target_file)}
        
        try:
            # recover=True 核心：容忍 HTML 语法错误
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(target_file, parser)
            root = tree.getroot()
            
            # 2. 解析 Contexts (使用 .xpath 替代 findall)
            contexts = self._parse_contexts(root)
            
            raw_date = self._get_document_period_end_date(root) # 先拿原始数据
            
            # [新增] 强制日期标准化逻辑
            if raw_date:
                try:
                    dt = date_parser.parse(raw_date)
                    extracted_data['Period End Date'] = dt.strftime("%Y-%m-%d") # 转为 2023-09-30
                except:
                    extracted_data['Period End Date'] = raw_date # 兜底
            else:
                return None # 如果没日期，直接丢弃

            target_date = extracted_data['Period End Date']

            # 4. 提取数据
            for metric_name, tags in self.metrics_map.items():
                val = self._extract_value(root, tags, contexts, target_date)
                extracted_data[metric_name] = val

            # Document Type
            doc_type = self._get_text_safe(root, "DocumentType")
            if doc_type:
                extracted_data['Source'] = doc_type
            
            return extracted_data

        except Exception as e:
            print(f"❌ [Parser] Critical Error in {os.path.basename(target_file)}: {e}")
            return None

    def _parse_contexts(self, root):
        contexts = {}
        # 🔥 FIX: 使用 .xpath 支持 local-name()
        # 查找所有 local-name 为 'context' 的节点
        context_nodes = root.xpath(".//*[local-name()='context']")
        
        for context in context_nodes:
            c_id = context.get("id")
            if not c_id: continue

            info = {'has_segment': False}
            
            # 检查 Segment (使用 xpath 检查是否存在)
            # xpath 返回的是 list，非空即为 True
            segment_check = context.xpath(".//*[local-name()='entity']//*[local-name()='segment']")
            if segment_check:
                info['has_segment'] = True
            
            # 解析日期
            # 1. Duration (Start/End)
            start_node = context.xpath(".//*[local-name()='period']//*[local-name()='startDate']")
            end_node = context.xpath(".//*[local-name()='period']//*[local-name()='endDate']")
            
            # 2. Instant (Instant)
            instant_node = context.xpath(".//*[local-name()='period']//*[local-name()='instant']")
            
            raw_end_date = None
            if start_node and end_node:
                raw_end_date = self._get_node_text(end_node[0])
            elif instant_node:
                raw_end_date = self._get_node_text(instant_node[0])
            
            # [新增] Context 日期也必须转为 ISO 格式
            if raw_end_date:
                try:
                    info['end'] = date_parser.parse(raw_end_date).strftime("%Y-%m-%d")
                except:
                    info['end'] = raw_end_date
            
            contexts[c_id] = info
        return contexts

    def _get_document_period_end_date(self, root):
        # 策略 A: 纯 XML
        nodes = root.xpath(".//*[local-name()='DocumentPeriodEndDate']")
        if nodes: return self._get_node_text(nodes[0])

        # 策略 B: iXBRL (HTML)
        # 查找 name 属性包含 'DocumentPeriodEndDate' 的 nonNumeric 标签
        nodes_ix = root.xpath(".//*[local-name()='nonNumeric'][contains(@name, 'DocumentPeriodEndDate')]")
        if nodes_ix: return self._get_node_text(nodes_ix[0])
            
        return None

    def _extract_value(self, root, tag_list, contexts, target_date):
        candidate_nodes = []
        
        # 1. 查找所有可能的节点
        for tag in tag_list:
            # XML: 直接匹配 tag
            xml_hits = root.xpath(f".//*[local-name()='{tag}']")
            candidate_nodes.extend(xml_hits)
            
            # iXBRL: 匹配 name 属性包含 tag 的 nonFraction
            # 使用 xpath 的 contains 函数，非常高效
            ix_hits = root.xpath(f".//*[local-name()='nonFraction'][contains(@name, '{tag}')]")
            candidate_nodes.extend(ix_hits)

        # 2. 遍历筛选
        for node in candidate_nodes:
            context_ref = node.get("contextRef")
            if not context_ref or context_ref not in contexts: continue
            
            ctx = contexts[context_ref]
            if ctx['has_segment']: continue
            
            if ctx.get('end') == target_date:
                raw_text = self._get_node_text(node)
                if not raw_text: continue

                try:
                    clean_val = re.sub(r'[^\d.-]', '', raw_text)
                    if not clean_val: continue
                    value = float(clean_val)

                    # Scale & Sign 处理
                    scale = node.get("scale")
                    if scale:
                        try:
                            value = value * (10 ** int(scale))
                        except: pass
                    
                    sign = node.get("sign")
                    if sign == "-":
                        value = value * -1
                        
                    return value
                except:
                    continue
        return 0.0

    def _get_text_safe(self, root, name):
        # XML
        nodes = root.xpath(f".//*[local-name()='{name}']")
        if nodes: return self._get_node_text(nodes[0])
        
        # iXBRL
        nodes_ix = root.xpath(f".//*[local-name()='nonNumeric'][contains(@name, '{name}')]")
        if nodes_ix: return self._get_node_text(nodes_ix[0])
        
        return None

    def _get_node_text(self, node):
        if node is None: return None
        return "".join(node.itertext()).strip()