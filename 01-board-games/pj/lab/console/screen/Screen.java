package console.screen;

/**
 * 用于模拟一个显示字符的屏幕
 */
public interface Screen {

    // 设置指定位置的字符
    void print(int row, int col, char c);

    // 设置指定位置开始的一串字符串
    void print(int row, int col, String s);

    void outputToConsole();

}
