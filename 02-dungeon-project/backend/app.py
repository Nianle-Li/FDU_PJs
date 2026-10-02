"""
Flask backend main entry
"""
from flask import Flask, jsonify, request, send_from_directory, redirect
from flask import Response
from flask_cors import CORS
from datetime import datetime
import os

from dungeon_service import DungeonService
from tree import TreasureTree
from adventure_log import AdventureLog

app = Flask(__name__)
CORS(app)

# 全局变量
service = DungeonService()
treasure_tree = TreasureTree()
log = AdventureLog()

# Frontend directory absolute path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', 'frontend'))
IMG_DIR = os.path.join(FRONTEND_DIR, 'static', 'img')

from config import DEBUG
if DEBUG:
    print(f"Frontend dir: {FRONTEND_DIR}")
    print(f"Frontend exists: {os.path.exists(FRONTEND_DIR)}")


# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """根路由 - 重定向到前端页面"""
    return redirect('/frontend/index.html')


@app.route('/frontend/')
@app.route('/frontend/<path:filename>')
def serve_frontend(filename='index.html'):
    """提供前端静态文件服务"""
    try:
        # 为了避免浏览器缓存导致旧页面仍被展示，对于主页面添加无缓存头
        resp = send_from_directory(FRONTEND_DIR, filename)
        # 仅对HTML文件（特别是index.html）添加强制不缓存头
        if filename.endswith('.html'):
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
        return resp
    except Exception as e:
        return jsonify({
            "error": "file_not_found",
            "message": str(e),
            "frontend_dir": FRONTEND_DIR,
            "requested_file": filename
        }), 404


@app.route('/api')
def api_root():
    """API 文档"""
    return jsonify({
        "name": "Dungeon Explorer API",
        "version": "1.0.0",
        "endpoints": {
            "dungeon_management": "GET /api/dungeon/new",
            "path_planning": "POST /api/path/shortest, POST /api/path/all-ranked",
            "player_actions": "POST /api/player/move",
            "boss_status": "GET /api/boss/status",
            "treasure_tree": "GET /api/treasure/tree",
            "log_history": "GET /api/log/history",
            "compose_icon": "GET /api/icon?type=room|monster|treasure|boss&lines=...&scale=1.0"
        }
    })


# ==================== API 路由 ====================

@app.route('/api/dungeon/new', methods=['GET'])
def generate_dungeon():
    """生成空房间框架（前端将生成布局后调用commit_layout完成地图）"""
    try:
        global treasure_tree, log
        num_rooms = int(request.args.get('num_rooms', 20))
        data = service.create_empty_dungeon(num_rooms)
        # 重置战利品树和探险日志
        treasure_tree = TreasureTree()
        log.clear()
        # 开始新的探索会话
        log.start_session(start_room=0, initial_power=10)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dungeon/graph', methods=['GET'])
def get_dungeon_graph():
    """获取当前地图结构"""
    try:
        if not service.graph.rooms:
            return jsonify({"error": "No dungeon generated yet"}), 404
        
        rooms = [room.to_dict() for room in service.graph.rooms.values()]
        
        return jsonify({
            "rooms": rooms,
            "boss_room_id": service.boss_room_id,
            "player": service.player.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room_details(room_id):
    """获取指定房间详情"""
    try:
        room = service.graph.rooms.get(room_id)
        if not room:
            return jsonify({"error": f"Room {room_id} not found"}), 404
        
        return jsonify(room.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dungeon/commit_layout', methods=['POST'])
def commit_layout():
    """接收前端布局，基于该布局分配怪物道具并确保可解，返回完整地图数据"""
    try:
        data = request.json or {}
        positions = data.get('positions', [])
        edges = data.get('edges', [])

        # update_layout 内部已经包含：
        # 1. 更新布局（位置和邻居关系）
        # 2. 分配宝箱（_assign_treasures）
        # 3. 分配怪物（_assign_monsters）
        # 4. 验证可解性（_ensure_solvability）
        # 5. 更新Boss房间ID和玩家状态
        service.update_layout(positions, edges)

        # 返回完整的地图数据（包含调整后的怪物和宝箱）
        rooms = [r.to_dict() for r in service.graph.rooms.values()]
        return jsonify({
            "success": True, 
            "rooms": rooms,
            "boss_room_id": service.boss_room_id,
            "player": service.player.to_dict(),
            "visited_rooms": list(service.player.visited_rooms)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/path/shortest', methods=['GET'])
def find_shortest_path():
    """
    计算最短路径（BFS - 探索次数最少）
    
    查询参数:
        - from: 起始房间ID (默认 0)
        - to: 目标房间ID (必需)
        - player_power: 玩家当前武力值 (默认 10)
        - details: 是否返回详细信息 (默认 true)
    
    返回:
        {
            "path": [房间ID列表],
            "length": 探索次数,
            "details": {路径详细信息} (可选)
        }
    """
    try:
        start = int(request.args.get('from', 0))
        end = request.args.get('to')
        player_power = int(request.args.get('player_power', 10))
        show_details = request.args.get('details', 'true').lower() == 'true'
        
        if end is None:
            return jsonify({"error": "missing_parameter", "parameter": "to"}), 400
        
        end = int(end)
        path = service.graph.bfs_shortest_path(start, end, player_power)
        
        if not path:
            return jsonify({
                "error": "path_not_found",
                "message": f"无法找到从房间 {start} 到房间 {end} 的路径"
            }), 404
        
        result = {
            "path": path,
            "length": len(path) - 1,
            "start": start,
            "end": end
        }
        
        # 添加详细信息
        if show_details:
            path_details = service.graph.get_path_details(path, player_power)
            result["details"] = path_details
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/path/all', methods=['GET'])
def get_all_ranked_paths():
    """
    获取所有可行路径并按价值排序（DFS）
    
    查询参数:
        - from: 起始房间ID (默认 0)
        - to: 目标房间ID (必需)
        - player_power: 玩家当前武力值 (默认 10)
        - limit: 返回路径数量限制 (默认 5, 最大 20)
        - details: 是否返回每条路径的详细信息 (默认 false)
    
    返回:
        {
            "paths": [
                {
                    "path": [房间ID列表],
                    "value": 战利品总价值,
                    "length": 路径长度,
                    "power_boost": 总武力提升,
                    "details": {详细信息} (可选)
                },
                ...
            ],
            "total_count": 找到的路径总数,
            "start": 起始房间,
            "end": 目标房间
        }
    """
    try:
        start = int(request.args.get('from', 0))
        end = request.args.get('to')
        power = int(request.args.get('player_power', 10))
        limit = min(int(request.args.get('limit', 5)), 5)  # 默认5条，最多返回5条
        show_details = request.args.get('details', 'false').lower() == 'true'
        
        if end is None:
            return jsonify({"error": "missing_parameter", "parameter": "to"}), 400
        
        end = int(end)
        
        # 找到所有可行路径
        paths = service.graph.dfs_all_feasible_paths(start, end, power)
        from config import DEBUG
        if DEBUG:
            print(f"\n=== 多路径搜索结果 ===")
            print(f"起点: {start}, 终点: {end}, 初始战力: {power}")
            print(f"找到 {len(paths)} 条可行路径")
        
        if not paths:
            return jsonify({
                "paths": [],
                "total_count": 0,
                "start": start,
                "end": end,
                "message": "未找到可行路径"
            })
        
        # 按宝箱带来的总武力提升排序（将道具价值等价为武力提升）
        scored = []  # list of (path, power_boost)
        for path in paths:
            total_boost = 0
            for room_id in path:
                room = service.graph.get_room(room_id)
                if room and room.treasure:
                    total_boost += room.treasure.value
            scored.append((path, total_boost))

        # 按 power_boost 降序排序
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)

        if DEBUG:
            print(f"\n按武力提升排序结果（前{min(5, len(ranked))}条）：")
            for i, (path, boost) in enumerate(ranked[:5]):
                print(f"  #{i+1}: 路径={path}, 武力提升={boost}")

        # 限制返回数量并构建结果
        result_paths = []
        for path, boost in ranked[:limit]:
            path_info = {
                "path": path,
                # value 字段等价为总武力提升，便于前端一致显示
                "value": boost,
                "length": len(path) - 1
            }

            path_info["power_boost"] = boost

            # 添加详细信息（可选）
            if show_details:
                path_details = service.graph.get_path_details(path, power)
                path_info["details"] = path_details

            result_paths.append(path_info)
        
        if DEBUG:
            print(f"\n返回前 {len(result_paths)} 条路径（总共 {len(paths)} 条）")
            print("=" * 50 + "\n")
        
        return jsonify({
            "paths": result_paths,
            "total_count": len(paths),
            "returned_count": len(result_paths),
            "start": start,
            "end": end
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/player/move', methods=['POST'])
def move_player():
    """移动玩家到新房间并战斗"""
    try:
        data = request.json
        room_id = data.get('room_id')
        
        if room_id is None:
            return jsonify({"error": "missing_parameter", "parameter": "room_id"}), 400
        
        # 记录移动前的状态
        from_room = service.player.current_room
        power_before = service.player.power
        
        combat_mode = data.get('combat_mode', 'dice')
        result = service.move_to_room(room_id, combat_mode)
        
        # 如果获得战利品，添加到树
        if result.get('new_treasure'):
            from models import Treasure
            treasure_dict = result['new_treasure']
            treasure = Treasure(**treasure_dict)
            treasure_tree.add_treasure(treasure)
        
        # 记录步骤到当前会话（仅在成功时）
        if result['success']:
            # 构建步骤数据
            step_data = {
                'from_room': from_room,
                'to_room': room_id,
                'power_before': power_before,
                'power_after': result['power']
            }
            
            # 添加怪物信息
            if result.get('combat_log'):
                target_room = service.graph.get_room(room_id)
                if target_room and target_room.monster:
                    step_data['monster'] = {
                        'name': target_room.monster.name,
                        'power': target_room.monster.power,
                        'is_boss': target_room.monster.is_boss
                    }
                step_data['combat_result'] = result.get('combat_log')
            
            # 添加宝箱信息
            if result.get('new_treasure'):
                step_data['treasure'] = result['new_treasure']
            
            # 记录步骤
            log.add_step(step_data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/boss/status', methods=['GET'])
def boss_status():
    """获取Boss当前位置（轮询端点）"""
    try:
        return jsonify({
            "boss_room_id": service.boss_room_id,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/boss/move', methods=['POST'])
def move_boss():
    """Boss随机移动（支持攻击玩家）"""
    try:
        result = service.move_boss_randomly()
        return jsonify({
            "new_room_id": result['new_room_id'],
            "old_room_id": result['old_room_id'],
            "boss_room_id": result['new_room_id'],  # For backwards compatibility
            "is_attacking_player": result['is_attacking_player'],
            "message": f"Boss moved to room {result['new_room_id']}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/boss/pause', methods=['POST'])
def pause_boss_movement():
    """暂停Boss移动"""
    try:
        service.pause_boss_movement()
        return jsonify({
            "success": True,
            "message": "Boss movement paused"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/boss/resume', methods=['POST'])
def resume_boss_movement():
    """恢复Boss移动"""
    try:
        service.resume_boss_movement()
        return jsonify({
            "success": True,
            "message": "Boss movement resumed"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/boss/attack', methods=['POST'])
def boss_attack():
    """Boss攻击玩家（延迟触发）"""
    try:
        result = service.boss_attack_player()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/treasure/tree', methods=['GET'])
def get_treasure_tree():
    """获取战利品树（包含统计信息和收藏信息）"""
    try:
        tree_data = treasure_tree.to_dict()
        statistics = treasure_tree.get_statistics()
        total_value = treasure_tree.get_total_value()
        total_count = len(treasure_tree.get_all_treasures())
        favorites_count = treasure_tree.get_favorites_count()
        
        return jsonify({
            "tree": tree_data,
            "statistics": {
                "by_category": statistics,
                "total_count": total_count,
                "total_value": total_value,
                "favorites_count": favorites_count
            },
            "favorites": list(treasure_tree.favorites)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/treasure/favorite', methods=['POST'])
def toggle_favorite():
    """切换战利品收藏状态"""
    try:
        data = request.json
        treasure_name = data.get('treasure_name')
        
        if not treasure_name:
            return jsonify({"error": "missing_parameter", "parameter": "treasure_name"}), 400
        
        # 检查当前是否已收藏
        is_favorited = treasure_tree.is_favorite(treasure_name)
        
        if is_favorited:
            # 取消收藏
            success = treasure_tree.remove_favorite(treasure_name)
            action = "removed"
        else:
            # 添加收藏
            success = treasure_tree.add_favorite(treasure_name)
            action = "added"
        
        if success:
            return jsonify({
                "success": True,
                "action": action,
                "treasure_name": treasure_name,
                "is_favorite": not is_favorited
            })
        else:
            return jsonify({"error": "treasure_not_found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/treasure/favorites', methods=['GET'])
def get_favorites():
    """获取所有收藏的战利品"""
    try:
        favorites = treasure_tree.get_favorites()
        return jsonify({
            "favorites": [t.to_dict() for t in favorites],
            "count": len(favorites)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/log/history', methods=['GET'])
def get_adventure_history():
    """获取探险日志（包括当前活动会话）"""
    try:
        result = {
            'sessions': log.get_all(),
            'current_session': log.get_current_session(),
            'total_sessions': len(log.get_all())
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/combat/simulate', methods=['POST'])
def simulate_combat():
    """战斗模拟（扩展功能）"""
    try:
        data = request.json
        player_power = data.get('player_power', 10)
        monster_power = data.get('monster_power', 15)
        
        result = service.simulate_battle(player_power, monster_power)
        
        return jsonify({
            "victory": result,
            "message": "Player wins!" if result else "Player loses!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 图标合成（服务器端生成 SVG） ====================
@app.route('/api/icon', methods=['GET'])
def compose_icon():
    """生成带居中文本的房间图标 SVG。
    查询参数：
    - type: room|monster|treasure|boss
    - lines: 多行文本，使用'\n'分隔
    - scale: 字体缩放倍数（默认1.0）
    - size: 图标尺寸（默认300）
    - player: true/false 是否显示玩家标记（默认false）
    """
    try:
        icon_type = request.args.get('type', 'room')
        lines = request.args.get('lines', '')
        scale = float(request.args.get('scale', '1.0'))
        size = int(request.args.get('size', '300'))
        show_player = request.args.get('player', 'false').lower() == 'true'

        # 选择基础SVG路径
        base_map = {
            'room': 'room.svg',
            'monster': 'monster.svg',
            'treasure': 'treasure.svg',
            'boss': 'boss.svg'
        }
        base_filename = base_map.get(icon_type, 'room.svg')
        base_path = os.path.join(IMG_DIR, base_filename)

        # 读取原始 SVG 文件内容并嵌入（避免外链引用问题）
        svg_lines = lines.split('\n') if lines else []
        svgNS = 'http://www.w3.org/2000/svg'
        
        def esc(s: str) -> str:
            return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

        base_size = int(size * 0.1 * scale)
        line_height = int(base_size * 1.25)
        total_h = line_height * (len(svg_lines) if svg_lines else 1)
        start_y = int((size - total_h) / 2) + line_height

        svg_parts = []
        svg_parts.append(f"<svg xmlns='{svgNS}' width='{size}' height='{size}' viewBox='0 0 {size} {size}'>")
        
        # 读取并嵌入原始 SVG 内容，正确缩放到目标尺寸
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                base_svg = f.read()
                # 提取 SVG 内部元素和原始 viewBox
                import re
                # 提取原始 viewBox 以计算缩放比例
                vb_match = re.search(r'viewBox=["\']([^"\']+)["\']', base_svg)
                orig_vb = vb_match.group(1).split() if vb_match else ['0', '0', '96', '96']
                orig_w = float(orig_vb[2])
                orig_h = float(orig_vb[3])
                scale_factor = size / max(orig_w, orig_h)
                
                # 匹配 <svg ...> 和 </svg>，取中间内容
                match = re.search(r'<svg[^>]*>(.*)</svg>', base_svg, re.DOTALL)
                if match:
                    inner_content = match.group(1)
                    # 用 <g> 缩放始内容到目标尺寸
                    svg_parts.append(f"<g transform='scale({scale_factor})'>{inner_content}</g>")
                else:
                    # 如果解析失败，绘制备用背景
                    svg_parts.append(f"<rect width='{size}' height='{size}' fill='#999' rx='30'/>")
        else:
            # 文件不存在时绘制备用背景
            svg_parts.append(f"<rect width='{size}' height='{size}' fill='#999' rx='30'/>")

        # 叠加居中文本
        for idx, text in enumerate(svg_lines):
            y = start_y + idx * line_height
            svg_parts.append(
                f"<text x='{size/2}' y='{y}' text-anchor='middle' dominant-baseline='middle' "
                f"font-family='MV Boli, Comic Sans MS, cursive' font-size='{base_size}px' font-weight='bold' fill='#ffffff' "
                f"stroke='#000000' stroke-width='{max(3, int(base_size*0.22))}' stroke-linejoin='round' paint-order='stroke'>{esc(text)}</text>"
            )
        
        # 玩家标记现在由前端CSS处理，不再在SVG中绘制
        # 保留player参数是为了向后兼容，但不再使用

        svg_parts.append("</svg>")
        svg_str = ''.join(svg_parts)
        return Response(svg_str, mimetype='image/svg+xml')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 游戏状态管理API ====================

@app.route('/api/game/status', methods=['GET'])
def get_game_status():
    """获取游戏状态"""
    try:
        status = service.check_game_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# /api/game/state endpoint removed: Save-game functionality is no longer supported by the backend.

@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """重置游戏"""
    try:
        result = service.reset_game()
        
        # 同时清空日志和宝藏树
        global treasure_tree, log
        treasure_tree = TreasureTree()
        log = AdventureLog()
        
        return jsonify({
            **result,
            "message": "Game reset! Ready to start a new adventure."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    from config import DEBUG
    if DEBUG:
        print("=" * 60)
        print("🏰 Dungeon Explorer backend starting")
        print("=" * 60)
        print(f"Frontend dir: {FRONTEND_DIR}")
        print(f"Frontend exists: {os.path.exists(FRONTEND_DIR)}")
        print("=" * 60)
        print("Access URLs:")
        print("  http://localhost:5000/")
        print("  http://localhost:5000/api")
        print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
