import graphviz
import os

# Đặt biến môi trường nếu Graphviz chưa có trong PATH (chỉ dùng cho Windows, sửa đường dẫn nếu cần)
# os.environ["PATH"] += os.pathsep + 'C:/Program Files/Graphviz/bin'

def create_comparison_diagram():
    # Khởi tạo đồ thị
    dot = graphviz.Digraph('ArchitectureComparison', format='png')
    dot.attr(rankdir='TB', size='12,8', dpi='300', fontname='Arial')
    dot.attr('node', shape='box', style='filled, rounded', fontname='Arial', margin='0.2')

    # ==============================================================
    # CLUSTER 1: HỆ THỐNG BLACK-BOX TRUYỀN THỐNG
    # ==============================================================
    with dot.subgraph(name='cluster_blackbox') as c:
        c.attr(style='dashed', color='#d32f2f', label='Hệ thống EDR Truyền thống (Black-Box)', fontname='Arial-Bold', fontsize='16')
        
        c.node('A1', 'Tệp thực thi (PE)', fillcolor='#f5f5f5')
        c.node('A2', 'Mô hình ML Tĩnh', fillcolor='#e0e0e0')
        c.node('A3', 'Giám sát Hành vi Động', fillcolor='#e0e0e0')
        c.node('A4', 'Bộ tổng hợp (Hard-coded Rules)', shape='diamond', fillcolor='#ffcccb')
        c.node('A5', 'Quyết định: MALWARE', fillcolor='#ef5350', fontcolor='white')
        c.node('A6', '⁉️ Không giải thích được:\n- Không rõ đặc trưng tĩnh\n- Không rõ lý do tổng hợp', shape='note', fillcolor='#ffebee', fontcolor='#c62828')

        c.edge('A1', 'A2')
        c.edge('A1', 'A3')
        c.edge('A2', 'A4')
        c.edge('A3', 'A4')
        c.edge('A4', 'A5')
        c.edge('A5', 'A6', style='dotted')

    # ==============================================================
    # CLUSTER 2: HỆ THỐNG XAI ĐA TẦNG (ĐỀ XUẤT)
    # ==============================================================
    with dot.subgraph(name='cluster_xai') as c:
        c.attr(style='solid', color='#2e7d32', label='Hệ thống Đề xuất: Khung XAI Đa tầng', fontname='Arial-Bold', fontsize='16', penwidth='2')
        
        c.node('B1', 'Tệp thực thi ngụy trang (PE)', fillcolor='#e3f2fd')
        
        # Tầng tĩnh và giải thích
        c.node('B2', 'Phân tích Tĩnh (LightGBM)', fillcolor='#bbdefb')
        c.node('B2_XAI', 'Giải thích cục bộ: TreeSHAP', fillcolor='#c8e6c9', shape='ellipse')
        
        # Tầng động và log
        c.node('B3', 'Giám sát Honeypot Watchdog', fillcolor='#bbdefb')
        c.node('B3_XAI', 'Triggers: Entropy, Đổi đuôi', fillcolor='#c8e6c9', shape='ellipse')
        
        # Fusion
        c.node('B4', 'Tổng hợp Thích nghi (Adaptive Fusion)\nTính toán trọng số dựa trên Độ tin cậy', shape='diamond', fillcolor='#81c784')
        c.node('B5', 'Quyết định: MALWARE', fillcolor='#ef5350', fontcolor='white')
        
        # Lời giải thích tổng hợp
        c.node('B6', '✅ Giải thích Minh bạch Đa tầng:\n1. Báo cáo SHAP (Đặc trưng Tĩnh)\n2. Báo cáo Hành vi (Forensic Động)\n3. Lý do Fusion: Ghi đè do C_file thấp', shape='note', fillcolor='#e8f5e9', fontcolor='#2e7d32', penwidth='2')

        # Cấu trúc luồng XAI
        c.edge('B1', 'B2')
        c.edge('B1', 'B3')
        
        c.edge('B2', 'B2_XAI', style='dashed', dir='none')
        c.edge('B3', 'B3_XAI', style='dashed', dir='none')
        
        c.edge('B2', 'B4', label=' C_file (Thấp)')
        c.edge('B3', 'B4', label=' P_dynamic (Cao)')
        
        c.edge('B4', 'B5')
        c.edge('B5', 'B6', penwidth='2', color='#2e7d32')

    # Render ra file PNG
    dot.render('architecture_comparison', view=True)
    print("✅ Đã xuất thành công file ảnh: architecture_comparison.png")

if __name__ == '__main__':
    create_comparison_diagram()