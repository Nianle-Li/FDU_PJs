#include "file.h"
#include <time.h>

// 获取包含.map 后缀的文件名, 存储在数组中
void get_map_filenames(char map_filenames[MAX_FILES][MAX_FILENAME_LENGTH]) {
    DIR *dir;
    struct dirent *ent;
    dir = opendir(".");
    if (dir == NULL) {
        perror("无法打开目录");
        exit(EXIT_FAILURE);
    }
    int index = 0;
    while ((ent = readdir(dir))!= NULL && index < MAX_FILES) {
        char *filename = ent->d_name;
        size_t len = strlen(filename);
        if (len > 4 && strcmp(filename + len - 4, ".map") == 0) {
            strncpy(map_filenames[index], filename, MAX_FILENAME_LENGTH);
            index++;
        }
    }
    closedir(dir);
    // 若文件数量少于 MAX_FILES，将多余的数组元素置为空字符串
    for (int i = index; i < MAX_FILES; ++i) {
        map_filenames[i][0] = '\0';
    }
}

// 读取map文件名转换为菜单选项
void get_level_options(char level_options[MAX_FILES][MAX_FILENAME_LENGTH], char map_filenames[MAX_FILES][MAX_FILENAME_LENGTH]) {
    int index = 0;
    while (map_filenames[index][0]!= '\0' && index < MAX_FILES) {
        size_t len = strlen(map_filenames[index]);
        snprintf(level_options[index], MAX_FILENAME_LENGTH, "Start the <%.*s>", (int)(len - 4), map_filenames[index]);
        index++;
    }
    for (int i = index; i < MAX_FILES; ++i) {
        level_options[i][0] = '\0';
    }
}

// 将二维数组中的字符串存储到指针数组中
void storeStrings(char arr[][100], int rows, char *strPtrArr[]) {
    for (int i = 0; i < rows; ++i) {
        strPtrArr[i] = arr[i]; 
    }
}

// 查找map文件总过程
void find_map_files(char ori_level_options[MAX_FILES][MAX_FILENAME_LENGTH], char ori_level_map[MAX_FILES][MAX_FILENAME_LENGTH], char *level_options[MAX_FILES+1], char *level_map[MAX_FILES]) {
    get_map_filenames(ori_level_map);
    get_level_options(ori_level_options, ori_level_map);
    storeStrings(ori_level_options, MAX_FILES, level_options);
    storeStrings(ori_level_map, MAX_FILES, level_map);
    level_options[MAX_FILES] = "Exit";
}

//读取地图文件
void read_map_file(Map *map,const char *filename){
    FILE *fp = fopen(filename,"r");
    if (fp == NULL){
        perror("The map file cannot be opened");
        exit(EXIT_FAILURE);
    } 
    fscanf(fp, "%d %d",&map->rows, &map->cols);
    fscanf(fp,"%d %d",&map->player_X, &map->player_Y);
    for (int i = 0; i < map->rows; i++){
        for (int j = 0; j < map->cols; j++){
            fscanf(fp, "%d", &map->map[i][j]);
        }
    }
    map->treasure_num = remaining_treasure(map);
    fclose(fp);
}

// 保存游戏进度
void save_game_progress(const char *filename, Map *map, int consumption, int treasures_found, int mode_index) {
    FILE *fp = fopen(filename, "wb");
    if (fp == NULL) {
        perror("Failed to save game progress");
        return;
    }
    time_t current_time = time(NULL);
    fwrite(&current_time, sizeof(time_t), 1, fp);
    fwrite(&map->rows, sizeof(int), 1, fp);
    fwrite(&map->cols, sizeof(int), 1, fp);
    fwrite(&map->player_X, sizeof(int), 1, fp);
    fwrite(&map->player_Y, sizeof(int), 1, fp);
    fwrite(&map->treasure_num, sizeof(int), 1, fp);
    fwrite(map->map, sizeof(int), MAX_ROW * MAX_COL, fp);
    fwrite(&consumption, sizeof(int), 1, fp);
    fwrite(&treasures_found, sizeof(int), 1, fp);
    fwrite(&mode_index, sizeof(int), 1, fp);
    fclose(fp);
}

// 加载游戏进度
int load_game_progress(const char *filename, Map *map, int *consumption, int *treasures_found, int *mode_index, time_t *last_play_time) {
    FILE *fp = fopen(filename, "rb");
    if (fp == NULL) {
        return 0;
    }
    fread(last_play_time, sizeof(time_t), 1, fp);
    fread(&map->rows, sizeof(int), 1, fp);
    fread(&map->cols, sizeof(int), 1, fp);
    fread(&map->player_X, sizeof(int), 1, fp);
    fread(&map->player_Y, sizeof(int), 1, fp);
    fread(&map->treasure_num, sizeof(int), 1, fp);
    fread(map->map, sizeof(int), MAX_ROW * MAX_COL, fp);
    fread(consumption, sizeof(int), 1, fp);
    fread(treasures_found, sizeof(int), 1, fp);
    fread(mode_index, sizeof(int), 1, fp);
    fclose(fp);
    return 1;
} 

