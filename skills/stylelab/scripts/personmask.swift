// Writes a grayscale person mask PNG for every frame picture in a folder, on this Mac, with Apple's
// built-in Vision. Free, nothing uploaded. White = the person, black = everything else.
// make_assets.py runs this for you (make_assets.py "<style folder>" cutout). By hand:
//   swiftc -O personmask.swift -o personmask && ./personmask <frames_dir> <masks_dir>
// Frames: .png / .jpg / .jpeg. Each mask gets the same name with .png, so frame 00007.jpg -> 00007.png.
// Every frame gets a mask (a frame with nobody in it gets an all-black one) so the numbering never has a
// gap and ffmpeg can line the masks up with the video frame for frame.
import Foundation
import Vision
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: personmask <frames_dir> <masks_dir>"); exit(1) }
guard #available(macOS 12.0, *) else { print("This needs macOS 12 or newer."); exit(2) }

let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let exts: Set<String> = ["png", "jpg", "jpeg"]
let files = ((try? FileManager.default.contentsOfDirectory(atPath: inDir.path)) ?? [])
  .filter { exts.contains(($0 as NSString).pathExtension.lowercased()) }.sorted()
if files.isEmpty { print("No frames found in \(inDir.path)"); exit(3) }

let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8

var lastSize: (Int, Int)? = nil   // the size of the last real mask, reused for empty frames
var written = 0, empty = 0

// Saves one 8-bit grayscale picture of the given bytes.
func savePNG(_ bytes: Data, width: Int, height: Int, rowBytes: Int, to url: URL) -> Bool {
  guard let provider = CGDataProvider(data: bytes as CFData),
        let mask = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: rowBytes,
                           space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGBitmapInfo(rawValue: 0),
                           provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent),
        let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)
  else { return false }
  CGImageDestinationAddImage(dest, mask, nil)
  return CGImageDestinationFinalize(dest)
}

for (i, name) in files.enumerated() {
  autoreleasepool {   // frees each frame's pictures right away, so memory stays flat on long clips
    let outURL = outDir.appendingPathComponent((name as NSString).deletingPathExtension + ".png")
    var done = false
    if let src = CGImageSourceCreateWithURL(inDir.appendingPathComponent(name) as CFURL, nil),
       let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
      let handler = VNImageRequestHandler(cgImage: img, options: [:])
      try? handler.perform([request])
      if let buf = request.results?.first?.pixelBuffer {
        CVPixelBufferLockBaseAddress(buf, .readOnly)
        let w = CVPixelBufferGetWidth(buf), h = CVPixelBufferGetHeight(buf), row = CVPixelBufferGetBytesPerRow(buf)
        if let base = CVPixelBufferGetBaseAddress(buf) {
          let data = Data(bytes: base, count: row * h)
          done = savePNG(data, width: w, height: h, rowBytes: row, to: outURL)
          if done { lastSize = (w, h) }
        }
        CVPixelBufferUnlockBaseAddress(buf, .readOnly)
      }
      if !done {   // Vision found no one: an all-black mask keeps the numbering whole
        let (w, h) = lastSize ?? (max(img.width / 2, 1), max(img.height / 2, 1))
        done = savePNG(Data(count: w * h), width: w, height: h, rowBytes: w, to: outURL)
        if done { empty += 1 }
      }
    }
    if done { written += 1 }
  }
  if i % 40 == 0 || i == files.count - 1 { print("\(i + 1)/\(files.count)"); fflush(stdout) }
}
print("done \(written)/\(files.count) masks (\(empty) with nobody in them)")
exit(written == files.count ? 0 : 4)
