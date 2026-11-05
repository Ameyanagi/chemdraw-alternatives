// List on-screen windows. Argument: a process id, or text matched against the owner name.
// Output: "<windowID> <owner> <width>x<height> <title>".
import CoreGraphics
import Foundation

let argument = CommandLine.arguments.dropFirst().first ?? ""
let pid = Int(argument)
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
for window in windows where (window[kCGWindowLayer as String] as? Int) == 0 {
    let owner = window[kCGWindowOwnerName as String] as? String ?? ""
    let matches = pid.map { $0 == window[kCGWindowOwnerPID as String] as? Int } ?? (argument.isEmpty || owner.lowercased().contains(argument.lowercased()))
    guard matches else { continue }
    let bounds = window[kCGWindowBounds as String] as? [String: CGFloat] ?? [:]
    print(window[kCGWindowNumber as String] as? Int ?? 0, owner, "\(Int(bounds["Width"] ?? 0))x\(Int(bounds["Height"] ?? 0))", window[kCGWindowName as String] as? String ?? "")
}
