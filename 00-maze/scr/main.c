#include "ui.h"
#include "game_logic.h"
#include "file.h"

int main() {
    char ori_level_options[MAX_FILES][MAX_FILENAME_LENGTH];
    char ori_level_map[MAX_FILES][MAX_FILENAME_LENGTH];
    char *level_options[MAX_FILES+1];
    char *level_map[MAX_FILES];
    
    // 模式选项
    char *mode_options[]= {
        "0 :Real-time mode",
        "1 :Programming mode"
    };
    // 退出原因
    char *exit_reason[] = {
        "Congratulations! Xiao Huang has found all the treasures!\n",
        "The adventure is over because'Q'was pressed!\n",
        "The instruction in the programming mode is incorrect!\n"
    };
    // 提示信息
    char menu_hint[] = "\nControl methods:\nPress 'W' to move upwards\nPress 'S' to move downwards\nPress <Enter> to make a selection\n";
    char map_hint[] = 
        "\nPress'W'to move upward,press'S'to move downward\n"
        "Press'A'to move to the left,press'D'to move to the right\n"
        "Press'I'to stay still,press'Q'to end the adventure\n"
        "Press'Z'to undo an action,press'Y'to redo an action\n";
    Menu level_menu, mode_menu;
    Map map;
    Op *head = NULL;
    Op *current = NULL;
    int record_index = -1;
    level_menu.count = sizeof(level_options) / sizeof(level_options[0]);
    mode_menu.count = sizeof(mode_options) / sizeof(mode_options[0]);
    int consumption = 0;
    int treasures_found = 0;
    int exit_the_round = 0;
    char route[3000];
    char filename[50];
    int treasure_found[2] = {0, 0};
    char direction;

    find_map_files(ori_level_options, ori_level_map, level_options, level_map);
    welcome_interface();
    while (1) {
        intialize_the_data(&consumption, route, &level_menu, &mode_menu);
        render_the_menu(&level_menu, level_options, menu_hint, "Xiao Huang's wonderful Adventure!\n");
        level_menu.selected_index = get_selected_index(&level_menu, level_options, menu_hint, "Xiao Huang's wonderful Adventure!\n");
        if_end_the_game(&level_menu);
        read_map_file(&map, level_map[level_menu.selected_index]);
        whether_restore_history(level_map, route, mode_options, menu_hint, level_menu, &mode_menu, record_index,filename, &map, &consumption, &treasures_found);
        initialize_op_list(&head, &current, &map); 
        while (1) {
            render_the_map(&map);
            manifest_the_consumption(&consumption);
            set_hint(map_hint);
            while (1) {
                treasure_found[0] = treasure_found[1] = 0;
                exit_the_round = move_player(&current, &head, &map, route, mode_menu.selected_index, &consumption, &direction);
                if (exit_the_round) {
                    break;
                } // 此轮游戏结束
                if (direction != UNDO && direction != UNDO_ && direction != REDO && direction != REDO_) {
                    clear_redo(&current);
                } // 清空撤销记录
                // 添加操作链表节点
                add_op(&current, &head, consumption, &map, treasure_found, &direction);
                // 判断是否达到地图渲染条件（结束此轮循环）：实时模式或按下 ENTER 键
                if (mode_menu.selected_index == 0 || direction == ENTER) {
                    break;
                }
            }
            //游戏结束数据展示界面
            if (exit_the_round) {
                end_the_round_process (&exit_the_round, exit_reason, level_options, &record_index, route, &consumption, map, filename, level_menu, mode_menu);
                break;
            }
        }
    }
    
}
    

