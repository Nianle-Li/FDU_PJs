#ifndef FILE_H
#define FILE_H

#include <dirent.h>
#include "ui.h"

#define MAX_FILENAME_LENGTH 100
#define MAX_FILES 3

void get_map_filenames(char map_filenames[MAX_FILES][MAX_FILENAME_LENGTH]);
void get_level_options(char level_options[MAX_FILES][MAX_FILENAME_LENGTH], char map_filenames[MAX_FILES][MAX_FILENAME_LENGTH]);
void storeStrings(char arr[][100], int rows, char *strPtrArr[]);
void find_map_files(char ori_level_options[MAX_FILES][MAX_FILENAME_LENGTH], char ori_level_map[MAX_FILES][MAX_FILENAME_LENGTH], char *level_options[MAX_FILES+1], char *level_map[MAX_FILES]);
void read_map_file(Map *map, const char *filename);
void save_game_progress(const char *filename, Map *map, int consumption, int treasures_found, int mode_index);
int load_game_progress(const char *filename, Map *map, int *consumption, int *treasures_found, int *mode_index, time_t *last_play_time);
int remaining_treasure(Map *map);

#endif