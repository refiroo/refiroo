import AppKit
import Foundation
let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let notes = root.appendingPathComponent("guide/_coverage/notes/SH1-GUIDE")
let baseline = try JSONSerialization.jsonObject(with: Data(contentsOf: notes.appendingPathComponent("baseline.json"))) as! [String:String]
let regex = try NSRegularExpression(pattern: "/docs/screens/([^\\s)]+)")
var names = Set<String>()
for text in baseline.values {
 for match in regex.matches(in:text,range:NSRange(text.startIndex...,in:text)) {
  names.insert(String(text[Range(match.range(at:1),in:text)!]))
 }
}
let sorted = names.sorted()
for start in stride(from:0,to:sorted.count,by:50) {
 let batch = Array(sorted[start..<min(start+50,sorted.count)])
 let bitmap = NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:1500,pixelsHigh:1900,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
 NSGraphicsContext.saveGraphicsState()
 NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep:bitmap)
 NSColor.white.setFill(); NSRect(x:0,y:0,width:1500,height:1900).fill()
 for (index,name) in batch.enumerated() {
  let x = (index % 5)*300, y = 1900-(index/5+1)*190
  let image = NSImage(contentsOf:root.appendingPathComponent("guide/public/screens/"+name))!
  let scale = min(294/image.size.width,166/image.size.height)
  image.draw(in:NSRect(x:Double(x),y:Double(y)+166-image.size.height*scale,width:image.size.width*scale,height:image.size.height*scale))
  (name as NSString).draw(at:NSPoint(x:x,y:y+170),withAttributes:[.font:NSFont.systemFont(ofSize:10),.foregroundColor:NSColor.black])
 }
 NSGraphicsContext.restoreGraphicsState()
 try bitmap.representation(using:.png,properties:[:])!.write(to:notes.appendingPathComponent("screens-\(start/50+1).png"))
}
print("Created 6 inspection sheets.")
