#include "ui.h"
#include "game_logic.h"

//菜单头部        
void set_header(char *text_str) {
    system("cls");
    printf("%s\n",text_str);
}

//设置信息列表
void set_info_list(char **text_str_list, int count) {
    for (int i = 0; i < count; i++)
        printf("%s\n",text_str_list[i]);
}

//设置提示信息
void set_hint(char *text_str) {
    printf("%s\n", text_str);
}

//欢迎界面
void welcome_interface() {
    char *welcome_info[] = {
        "           Press any key to start!",
        "",
        "              ._____.._____.    ",
        "              | ._. | | ._. |    ",
        "              | !_| |_|_|_! |    ",
        "              !___| |_______!    ",
        "              .___|_|_| |___.    ",
        "              | ._____| |_. |    ",
        "              | !_! | | !_! |    ",
        "              !_____! !_____!    ",
        "",
        "**************************************************",
        "**          Welcome to the Maze World!          **",
        " **           All rights reserved             **",
        " ** Li Jianing, Software Engineering, Grade 24 **",
        "**                                              **",
        "**************************************************"
    };
    int info_count = sizeof(welcome_info) / sizeof(welcome_info[0]);
    set_header("Are you ready to start an adventure with brave Xiao Huang?");
    set_info_list(welcome_info, info_count);
    getch();
    system("cls");
}


//设置选择菜单的选项内容
void set_selection_options(Menu *menu, char **options) {
    menu->options = (Menu_option *)malloc(menu->count * sizeof(Menu_option));
    if (menu == NULL || options == NULL) {
        fprintf(stderr, "无效的参数传入\n");
        exit(EXIT_FAILURE);
    } 
    for(int i = 0; i < menu->count; i++) {
        menu->options[i].text = options[i];
    }  
    for (int i = 0; i < menu->count; i++) {
        if (i == menu->selected_index){
            printf("> %s\n", menu->options[i].text);
        }
        else{
            printf("  %s\n", menu->options[i].text);
        }
    }
}


//得到用户选择的选项索引
int get_selected_index(Menu *menu, char **options, char *hint, char* header) {
    while(1) {
        int key = getch();
        if ((key == UP || key == UP_) && menu->selected_index)
            menu->selected_index--;
        else if ((key == DOWN || key == DOWN_) && (menu->selected_index < menu->count - 1))
            menu->selected_index++;
        else if(key == ENTER) 
        return menu->selected_index;
        render_the_menu(menu, options, hint, header);
    }   
}

//渲染菜单
void render_the_menu(Menu *menu, char **options, char *text_str, char *header){
    set_header(header);
    set_selection_options(menu, options);
    set_hint(text_str);
}


//渲染地图
void render_the_map(Map *map) {
    system("cls");  
    for (int i = 0; i < map->rows; i++) {
        for (int j = 0; j < map->cols; j++) {
            if (i == map->player_Y && j == map->player_X) {
                printf("Y ");  
            } 
            else {
                switch (map->map[i][j]) {
                case 0:
                    printf("  ");
                    break;
                case 1:
                    printf("W ");
                    break;
                case 2:
                    printf("D ");
                    break;
                case 3:
                    printf("T ");
                    break;
                }
            }
        }
        printf("\n");
    }
}

// 展示玩家体力值消耗
void manifest_the_consumption(int *consumption) {
    printf ("Physical consumption:%d\n", *consumption);
}

// 显示加载进度菜单
void show_load_progress_menu(const char *filename, Map *map, int *consumption, int *treasures_found, int *mode_index) {
    time_t last_play_time;
    // 尝试加载游戏进度
    if (!load_game_progress(filename, map, consumption, treasures_found, mode_index, &last_play_time)) {
        *mode_index = -1; 
        return;
    }
    // 格式化上次游戏时间
    struct tm *time_info = localtime(&last_play_time);
    char time_str[100];
    if (time_info != NULL) {
        strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", time_info);
    } else {
        strcpy(time_str, "Unknown time");
    }
    //渲染加载进度菜单，获取用户选择  
    char header[200];
    sprintf(header, "Whether to load the game progress from last time?\nLast game time: %s\nThe number of treasures found: %d/%d", time_str, *treasures_found, map->treasure_num);
    char *options[] = {"Yes", "No"};
    Menu load_menu;
    load_menu.count = 2;
    load_menu.selected_index = 0;
    char hint[] = "\nControl methods:\nPress 'W' to move upwards\nPress 'S' to move downwards\nPress <Enter> to make a selection\n";
    render_the_menu(&load_menu, options, hint, header);
    int choice = get_selected_index(&load_menu, options, hint, header);
    // 用户若选择开启新一轮游戏，则删除存档
    if (choice == 1) {
        remove(filename);
        *mode_index = -1;
    }
}

//游戏结束界面
void end_the_game(){
    system("cls");
    printf("  _____                         ____                 \n");
    printf(" / ____|                       / __ \\                \n");
    printf("| |  __  __ _ _ __ ___   ___  | |  | |_   _____ _ __ \n");
    printf("| | |_ |/ _` | '_ ` _ \\ / _ \\ | |  | \\ \\ / / _ \\ '__|\n");
    printf("| |__| | (_| | | | | | |  __/ | |__| |\\ V /  __/ |   \n");
    printf(" \\_____|\\__,_|_| |_| |_|\\___|  \\____/  \\_/ \\___|_|   \n");
    printf("\n");
    printf("****************************************************\n");
    printf("**                                                **\n");
    printf("**                  GAME OVER                     **\n");
    printf("**                                                **\n");
    printf("****************************************************\n");
    printf("\n");
    printf ("You have successfully exited the game!\n");
    printf("Goodbye and may you have a nice day!");
    exit(EXIT_SUCCESS);
}

