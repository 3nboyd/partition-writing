import AppKit

func quote(_ value: String) -> String {
    return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
}

final class Launcher: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        let info = Bundle.main.infoDictionary ?? [:]
        guard let source = info["PartitionSource"] as? String,
              let python = info["PartitionPython"] as? String,
              let codex = info["PartitionCodex"] as? String,
              let mode = info["PartitionMode"] as? String else {
            fail("The launcher is missing its installation settings. Run the Mac installer again.")
            return
        }
        var arguments = [python, source + "/macos/start.py", "--codex", codex]
        if mode == "code" {
            let panel = NSOpenPanel()
            panel.title = "Partition Code"
            panel.message = "Choose the coding folder to open in Codex."
            panel.prompt = "Open folder"
            panel.canChooseDirectories = true
            panel.canChooseFiles = false
            panel.allowsMultipleSelection = false
            if panel.runModal() != .OK || panel.url == nil {
                NSApp.terminate(nil)
                return
            }
            arguments += ["--project", panel.url!.path]
        }
        do {
            let folder = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("Partition/Launches", isDirectory: true)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let command = folder.appendingPathComponent(UUID().uuidString + ".command")
            // Each argument is shell-quoted; selected folder names are never executable text.
            let script = "#!/bin/zsh\n" + arguments.map(quote).joined(separator: " ") + "\n"
            try script.write(to: command, atomically: true, encoding: .utf8)
            try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: command.path)
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/open")
            process.arguments = ["-a", "Terminal", command.path]
            try process.run()
            process.waitUntilExit()
            if process.terminationStatus != 0 {
                fail("Terminal could not open. Start the project from its command-line instructions.")
                return
            }
            NSApp.terminate(nil)
        } catch {
            fail(error.localizedDescription)
        }
    }
    func fail(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Partition could not start"
        alert.informativeText = message
        alert.runModal()
        NSApp.terminate(nil)
    }
}
let application = NSApplication.shared
let delegate = Launcher()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.activate(ignoringOtherApps: true)
application.run()
