package console.command;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;

import console.playground.PlayGround;

public class PlaybackCommand implements Command {
    private final PlayGround session;
    
    public PlaybackCommand(PlayGround session) {
        this.session = session;
    }
    
    @Override
    public void execute(String input) {
        // 解析文件名
        String[] parts = input.split("\\s+", 2);
        if (parts.length != 2) {
            throw new IllegalArgumentException("无效的回放命令，格式：playback filename.cmd");
        }
        
        String filename = parts[1];
        List<String> commands = new ArrayList<>();
        
        try {
            // 简化文件查找逻辑
            File file = new File(filename);
            // 如果不是绝对路径，尝试在几个常见位置查找
            if (!file.isAbsolute()) {
                String[] searchPaths = {
                    ".",                                           // 当前目录
                    "d:\\project\\vscode\\java_lab\\pj",           // 项目根目录
                    "d:\\project\\vscode\\java_lab\\pj\\lab",      // lab目录
                    "d:\\project\\vscode\\java_lab\\pj\\target\\classes" // classes目录
                };
                
                for (String path : searchPaths) {
                    File testFile = new File(path, filename);
                    if (testFile.exists()) {
                        file = testFile;
                        break;
                    }
                }
            }
            
            if (!file.exists()) {
                throw new IllegalArgumentException("找不到命令文件: " + filename);
            }
            
            // 读取文件内容
            try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (!line.isEmpty() && !line.startsWith("REM") && !line.startsWith("#")) {
                        commands.add(line);
                    }
                }
            }
            
            if (commands.isEmpty()) {
                throw new IllegalArgumentException("命令文件为空或只包含注释: " + filename);
            }
            
            // 设置回放命令和延迟时间
            session.startPlayback(commands, 1000);
            
        } catch (Exception e) {
            throw new RuntimeException("读取回放文件失败: " + e.getMessage(), e);
        }
    }

    @Override
    public boolean canAccept(String input) {
        return input != null && input.toLowerCase().startsWith("playback");
    }

    @Override
    public String prompt() {
        return "演示模式(playback filename.cmd)";
    }

    @Override
    public boolean isEnabled() {
        return true;
    }
}
