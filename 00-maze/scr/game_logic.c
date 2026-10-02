#include "game_logic.h"
#include "ui.h"

Map initial_map;

// 链表初始化
void initialize_op_list(Op **head, Op **current, Map *map) {
    Op *temp;
    while (*head!= NULL) {
        temp = *head;
        *head = (*head)->next;
        free(temp);
    }
    *head = NULL;
    *current = NULL;
    initial_map = *map;
}

void intialize_the_data(int *consumption, char *route, Menu *level_menu, Menu *mode_menu) {
    level_menu->selected_index = 0;
    mode_menu->selected_index = 0;
    *consumption = 0;
    route[0] = '\0'; 
}

void if_end_the_game(Menu *level_menu) {
    if (level_menu->selected_index == 3) {
        end_the_game();
    }
}

// 添加操作记录到链表
void add_op(Op **current, Op **head, int consumption, Map *map, int *treasure_found, char *direction) {
    switch(*direction) {
    case UP: case UP_: case DOWN: case DOWN_: case RIGHT: case RIGHT_: case LEFT: case LEFT_: case STILL: case STILL_: {
        Op *new_op = (Op*)malloc(sizeof(Op));
        new_op->consumption = consumption;
        new_op->player.x = map->player_X;
        new_op->player.y = map->player_Y;
        new_op->consumption = consumption;
        for (int i = 0; i < 2; i++) {
            new_op->treasure_found[i] = treasure_found[i];
        }
        new_op->next = NULL;
        new_op->prev = NULL;
        if (*head == NULL) {
            *head = new_op;
            *current = new_op;  
        } 
        else {
            (*current)->next = new_op;
            new_op->prev = *current;
            *current = new_op;
        }
        break;
    }
    default:
        break;
    }
}

// 清空撤销记录
void clear_redo(Op **current) {
    if (*current != NULL) {
        Op *temp = (*current)->next;
        while (temp != NULL) {
            Op *next = temp->next;
            free(temp);
            temp = next;
        }
        (*current)->next = NULL;
    }
}

// 撤销操作
void undo(Op **current, Op **head, Map *map, int *consumption) {
    if (*current != NULL && (*current)->prev != NULL) {
        *current = (*current)->prev;
        map->player_X = (*current)->player.x;
        map->player_Y = (*current)->player.y;
        *consumption = (*current)->consumption;
    } else {
        // 撤销到初始状态
        *map = initial_map;
        *consumption = 0;
    }
}

// 恢复操作
void redo(Op **current, Op **head, Map *map, int *consumption) {
    if (*current != NULL && (*current)->next != NULL) {
        *current = (*current)->next;
        map->player_X = (*current)->player.x;
        map->player_Y = (*current)->player.y;
        *consumption = (*current)->consumption;
    }
}

// 收集宝藏
void collect_the_treasure(Map *map){
    if (map->map[map->player_Y + 1][map->player_X] == 3){
        map->map[map->player_Y + 1][map->player_X] = 0;
    } 
    if (map->map[map->player_Y - 1][map->player_X] == 3){
        map->map[map->player_Y - 1][map->player_X] = 0;
    }
    if (map->map[map->player_Y][map->player_X + 1] == 3){
        map->map[map->player_Y][map->player_X + 1] = 0;
    }
    if (map->map[map->player_Y][map->player_X - 1] == 3){
        map->map[map->player_Y][map->player_X - 1] = 0;
    }
}

//统计剩余宝藏数量
int remaining_treasure(Map *map) {
    int num = 0;
    for (int i = 0; i < map->rows; i++) {
        for (int j = 0; j < map->cols; j++) {
            if (map->map[i][j] == 3) { // 3 表示宝藏
                num++;
            }
        }
    }
    return num;
}

// 处理玩家单步移动
int move_player (Op **current, Op **head,  Map *map, char *route,int mode_index, int *consumption, char *direction){
    int routeNum = strlen(route); 
    input_again: 
    *direction = getch ();
    switch (*direction){
    case STILL:
    case STILL_:break;
    case UNDO:
    case UNDO_:undo(current, head, map, consumption);(*consumption)--;break; 
    case REDO:
    case REDO_:redo(current, head, map, consumption);(*consumption)--;break; 
    case QUIT_:
    case QUIT:
        return 2;
    case UP_:
    case UP:        
        if (map->map[map->player_Y - 1][map->player_X] == 1) 
            break;
        if (map->map[map->player_Y][map->player_X] == 2) 
            (*consumption)++;
        map->player_Y--;
        clear_redo(current);
        route[routeNum++] = 'U'; 
        route[routeNum] = '\0';
        break;
    case DOWN:
    case DOWN_:
        if (map->map[map->player_Y + 1][map->player_X] == 1)
            break;
        if (map->map[map->player_Y][map->player_X] == 2)
            (*consumption)++;
        map->player_Y++;
        clear_redo(current);
        route[routeNum++] = 'D'; 
        route[routeNum] = '\0';
        break;
    case RIGHT:
    case RIGHT_:
        if (map->map[map->player_Y][map->player_X + 1] == 1)
            break;
        if (map->map[map->player_Y][map->player_X] == 2)
            (*consumption)++;
        map->player_X++;
        clear_redo(current);
        route[routeNum++] = 'R'; 
        route[routeNum] = '\0'; 
        break;
    case LEFT:
    case LEFT_:
        if (map->map[map->player_Y][map->player_X - 1] == 1)
            break;
        if (map->map[map->player_Y][map->player_X] == 2)
            (*consumption)++;
        map->player_X--;
        clear_redo(current);
        route[routeNum++] = 'L'; 
        route[routeNum] = '\0';
        break;
    case ENTER:
        if (mode_index) { // 此时为编程模式
            return 0; // 标志合法输入
        }
        printf ("Input error. Please enter again.\n");
        (*consumption)--;
        goto input_again;
    default:
        if (mode_index) { // 此时为编程模式
            return 3; // 标志非法输入
        } else {
            printf ("Input error. Please enter again.\n");
            goto input_again;   //实时模式非法输入视为无效输入，继续等待输入
        }
    }
    (*consumption)++;
    collect_the_treasure(map);
    if (!remaining_treasure(map)) {
        return 1; // 玩家赢得游戏
    }
    return 0; // 标志合法输入
}

//一轮游戏结束后的处理逻辑
void end_the_round_process (int *exit_the_round,char *exit_reason[], char *level_options[], int *record_index, char *route, int *consumption, Map map, char *filename, Menu level_menu, Menu mode_menu ) {  
    set_header(exit_reason[*exit_the_round - 1]);
    printf("Route of action: %s\n", route);
    printf("The amount of physical strength Xiao Huang consumed: %d\n", *consumption);
    printf("The number of treasures Xiao Huang found: %d\n", map.treasure_num - remaining_treasure(&map));
    printf("Press any key to continue.");
    // 保存游戏进度
    sprintf(filename, "level_%d.record_map", level_menu.selected_index);
    save_game_progress(filename, &map, *consumption, map.treasure_num - remaining_treasure(&map), mode_menu.selected_index);
    // 标记存档的关卡索引
    *record_index = level_menu.selected_index;
    level_options[0] = (*record_index == 0) ?"Start the ordinary journey(history record)": "Start the ordinary journey";
    level_options[1] = (*record_index == 1) ? "Start the grand journey(history record)": "Start the grand journey";
    level_options[2] = (*record_index == 2) ? "Start the devil's journey(history record)": "Start the devil's journey";
    getch();   
}

//处理恢复历史记录相关逻辑
void whether_restore_history(char *level_map[], char route[],char *mode_options[], char menu_hint[], Menu level_menu, Menu *mode_menu, int record_index, char *filename, Map *map, int *consumption, int *treasures_found){
    if(level_menu.selected_index == record_index) {
        show_load_progress_menu(filename, map, consumption, treasures_found, &(mode_menu->selected_index));
        // 用户选择重新开始
        if (mode_menu->selected_index == -1) {
            mode_menu->selected_index = 0;
            render_the_menu(mode_menu, mode_options, menu_hint, "Please select the control mode:\n");
            mode_menu->selected_index = get_selected_index(mode_menu, mode_options, menu_hint, "Please select the control mode:\n");
            read_map_file(map, level_map[level_menu.selected_index]);
            *consumption = 0; 
            route[0] = '\0'; 
        }
    }
    else {
        render_the_menu(mode_menu, mode_options, menu_hint, "Please select the control mode:\n");
        mode_menu->selected_index = get_selected_index(mode_menu, mode_options, menu_hint, "Please select the control mode:\n");
    }
}

