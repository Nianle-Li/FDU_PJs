#ifndef GAME_LOGIC_H
#define GAME_LOGIC_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h> 
#include "ui.h"

void initialize_op_list(Op **head, Op **current, Map *map);
void intialize_the_data(int *consumption, char *route, Menu *level_menu, Menu *mode_menu);
void if_end_the_game(Menu *level_menu);
void add_op(Op **current, Op **head, int consumption, Map *map, int *treasure_found, char *direction); 
void undo(Op **current, Op **head, Map *map, int *consumption);
void redo(Op **current, Op **head, Map *map, int *consumption);
void clear_redo(Op **current);
void collect_the_treasure(Map *map);
int move_player(Op **current, Op **head, Map *map, char *route, int mode_index, int *consumption, char *direction);
int remaining_treasure(Map *map);
void read_map_file(Map *map, const char *filename);
void save_game_progress(const char *filename, Map *map, int consumption, int treasures_found, int mode_index);
void whether_restore_history(char *level_map[], char route[],char *mode_options[], char menu_hint[], Menu level_menu, Menu *mode_menu, int record_index, char *filename, Map *map, int *consumption, int *treasures_found);
void end_the_round_process (int *exit_the_round,char *exit_reason[], char *level_options[], int *record_index, char *route, int *consumption, Map map, char *filename, Menu level_menu, Menu mode_menu);

#endif