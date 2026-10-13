// Cut one car out of a picture with Apple's Vision (macOS 14+), for the private garage.
//   swift scripts/lift_car.swift <picture> <out.png> [x y width height]  (crop from the top-left)
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count == 3 || args.count == 7, let src = CIImage(contentsOf: URL(fileURLWithPath: args[1])) else {
  print("usage: swift lift_car.swift <picture> <out.png> [x y width height]"); exit(1)
}
var piece = src
if args.count == 7 {  // CoreImage counts from the bottom; the crop is given from the top
  let n = args[3...6].compactMap { Double($0) }.map { CGFloat($0) }
  let rect = CGRect(x: n[0], y: src.extent.height - n[1] - n[3], width: n[2], height: n[3])
  piece = src.cropped(to: rect).transformed(by: CGAffineTransform(translationX: -rect.minX, y: -rect.minY))
}
let request = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(ciImage: piece)
try handler.perform([request])
guard let result = request.results?.first else { print("No car found."); exit(1) }
let lifted = try result.generateMaskedImage(ofInstances: result.allInstances, from: handler,
                                            croppedToInstancesExtent: true)
try CIContext().writePNGRepresentation(of: CIImage(cvPixelBuffer: lifted),
                                       to: URL(fileURLWithPath: args[2]), format: .RGBA8,
                                       colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
print("Saved \(args[2])")
