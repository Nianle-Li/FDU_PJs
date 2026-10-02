#ifndef UI_H
#define UI_H

#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <string.h> 
#include <windows.h>
#include <time.h>

#define MAX_ROW 21
#define MAX_COL 21

typedef enum {
    STILL = 'I',
    STILL_ = 'i',
    UNDO = 'Z',
    UNDO_ = 'z',
    QUIT = 'Q',
    QUIT_ = 'q',    
    REDO = 'Y',
    REDO_ = 'y',    
    UP = 'W',
    UP_ = 'w',  
    DOWN = 'S',
    DOWN_ = 's',
    LEFT = 'A',
    LEFT_ = 'a',
    RIGHT = 'D',
    RIGHT_ = 'd',
    ENTER = 13
} Direction;


typedef struct {
    int rows;
    int cols;
    int map[MAX_ROW][MAX_COL];
    int player_X;
    int player_Y;
    int treasure_num;
} Map;


typedef struct {
    int x;
    int y;
    int consumption;
} Player;


typedef struct Op {
    int consumption;
    Player player;
    int treasure_found[2];
    struct Op *prev;
    struct Op *next;
} Op;

typedef struct {
    char *text;
} Menu_option;

typedef struct {
    Menu_option *options; 
    int count; 
    int selected_index; 
} Menu;

void set_header(char *text_str);
void set_info_list(char **text_str_list, int count);
void set_selection_options(Menu *menu, char **options);
void set_hint(char *text_str);
void manifest_the_consumption(int *consumption);
int get_selected_index(Menu *menu, char **options, char *hint, char *header);
void render_the_menu(Menu *menu, char **options, char *text_str, char *header); 
void render_the_map(Map *map);
void welcome_interface();
int load_game_progress(const char *filename, Map *map, int *consumption, int *treasures_found, int *mode_index, time_t *last_play_time);
void show_load_progress_menu(const char *filename, Map *map, int *consumption, int *treasures_found, int *mode_index);
void end_the_game();


#endif
