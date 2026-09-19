import Foundation
import Vision
import AppKit

// Local OCR only. Output boxes use top-left image-relative coordinates.
struct Line: Codable {
    var text: String
    var confidence: Float
    var bbox: [Double]
}
struct Page: Codable {
    var source: String
    var width: Int
    var height: Int
    var lines: [Line]
}
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
for input in CommandLine.arguments.dropFirst() {
    do {
        let url = URL(fileURLWithPath: input)
        let output = url.deletingPathExtension().appendingPathExtension("ocr.json")
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["zh-Hans", "en-US"]
        request.usesLanguageCorrection = true
        request.minimumTextHeight = 0.003
        let handler = VNImageRequestHandler(url: url, options: [:])
        try handler.perform([request])
        let bitmap = NSBitmapImageRep(data: try Data(contentsOf: url))!
        let lines = (request.results ?? []).compactMap { obs -> Line? in
            guard let c = obs.topCandidates(1).first else { return nil }
            let b = obs.boundingBox
            return Line(text: c.string, confidence: c.confidence, bbox: [b.minX, 1-b.maxY, b.maxX, 1-b.minY])
        }
        let page = Page(source: input, width: bitmap.pixelsWide, height: bitmap.pixelsHigh, lines: lines)
        try encoder.encode(page).write(to: output)
        print("\(url.lastPathComponent): \(lines.count) lines -> \(output.lastPathComponent)")
        fflush(stdout)
    } catch {
        fputs("OCR failed for \(input): \(error)\n", stderr)
        exit(1)
    }
}
