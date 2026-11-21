// Snapshot device settings and capture bounded integer PCM through AudioQueue.
import Foundation
import CoreAudio
import AudioToolbox

struct Failure: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}

func checked(_ status: OSStatus, _ operation: String) throws {
    if status != noErr { throw Failure("\(operation) failed (OSStatus \(status))") }
}

func address(_ selector: AudioObjectPropertySelector,
             _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal) -> AudioObjectPropertyAddress {
    AudioObjectPropertyAddress(mSelector: selector, mScope: scope, mElement: kAudioObjectPropertyElementMain)
}

func number<T>(_ object: AudioObjectID, _ selector: AudioObjectPropertySelector, _ initial: T) throws -> T {
    var value = initial
    var property = address(selector)
    var size = UInt32(MemoryLayout<T>.size)
    let status = withUnsafeMutablePointer(to: &value) {
        AudioObjectGetPropertyData(object, &property, 0, nil, &size, $0)
    }
    try checked(status, "Read audio property")
    return value
}

func text(_ object: AudioObjectID, _ selector: AudioObjectPropertySelector) throws -> String {
    var value: CFString? = nil
    var property = address(selector)
    var size = UInt32(MemoryLayout<CFString?>.size)
    let status = withUnsafeMutablePointer(to: &value) {
        AudioObjectGetPropertyData(object, &property, 0, nil, &size, $0)
    }
    try checked(status, "Read device identity")
    guard let value else { throw Failure("Device identity missing") }
    return value as String
}

func set<T>(_ object: AudioObjectID, _ selector: AudioObjectPropertySelector, _ value: T) throws {
    var value = value
    var property = address(selector)
    let status = withUnsafePointer(to: &value) {
        AudioObjectSetPropertyData(object, &property, 0, nil, UInt32(MemoryLayout<T>.size), $0)
    }
    try checked(status, "Set audio property")
}

func channels(_ id: AudioDeviceID, _ scope: AudioObjectPropertyScope) throws -> UInt32 {
    var property = address(kAudioDevicePropertyStreamConfiguration, scope)
    var size: UInt32 = 0
    try checked(AudioObjectGetPropertyDataSize(id, &property, 0, nil, &size), "Read stream layout")
    let storage = UnsafeMutableRawPointer.allocate(byteCount: Int(size), alignment: MemoryLayout<AudioBufferList>.alignment)
    defer { storage.deallocate() }
    try checked(AudioObjectGetPropertyData(id, &property, 0, nil, &size, storage), "Read stream channels")
    return UnsafeMutableAudioBufferListPointer(storage.assumingMemoryBound(to: AudioBufferList.self))
        .reduce(0) { $0 + $1.mNumberChannels }
}

struct Device: Codable {
    let id: AudioDeviceID
    let uid: String
    let name: String
    let rate: Double
    let inputChannels: UInt32
    let outputChannels: UInt32
}

func devices() throws -> [Device] {
    var property = address(kAudioHardwarePropertyDevices)
    var size: UInt32 = 0
    let system = AudioObjectID(kAudioObjectSystemObject)
    try checked(AudioObjectGetPropertyDataSize(system, &property, 0, nil, &size), "List devices")
    var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    try checked(AudioObjectGetPropertyData(system, &property, 0, nil, &size, &ids), "Read devices")
    return try ids.map { id in
        Device(id: id, uid: try text(id, kAudioDevicePropertyDeviceUID),
               name: try text(id, kAudioObjectPropertyName),
               rate: try number(id, kAudioDevicePropertyNominalSampleRate, Double(0)),
               inputChannels: try channels(id, kAudioObjectPropertyScopeInput),
               outputChannels: try channels(id, kAudioObjectPropertyScopeOutput))
    }
}

let defaults: [AudioObjectPropertySelector] = [kAudioHardwarePropertyDefaultInputDevice,
    kAudioHardwarePropertyDefaultOutputDevice, kAudioHardwarePropertyDefaultSystemOutputDevice]

struct Snapshot: Codable {
    let devices: [Device]
    let defaultUIDs: [String]
}

func snapshot() throws -> Snapshot {
    let all = try devices()
    let selected = try defaults.map { selector -> String in
        let id = try number(AudioObjectID(kAudioObjectSystemObject), selector, AudioDeviceID(0))
        guard let device = all.first(where: { $0.id == id }) else { throw Failure("Default device missing") }
        return device.uid
    }
    return Snapshot(devices: all, defaultUIDs: selected)
}

func restore(_ path: String) throws {
    let saved = try JSONDecoder().decode(Snapshot.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
    let current = try devices()
    guard saved.defaultUIDs.count == defaults.count else { throw Failure("Invalid audio snapshot") }
    let byUID = Dictionary(uniqueKeysWithValues: current.map { ($0.uid, $0) })
    for uid in saved.defaultUIDs {
        guard byUID[uid] != nil else { throw Failure("Saved default device is unavailable; retain the snapshot") }
    }
    for device in saved.devices {
        guard let active = byUID[device.uid] else { continue }
        if abs(active.rate - device.rate) > 0.01 {
            try set(active.id, kAudioDevicePropertyNominalSampleRate, device.rate)
        }
    }
    for (selector, uid) in zip(defaults, saved.defaultUIDs) {
        try set(AudioObjectID(kAudioObjectSystemObject), selector, byUID[uid]!.id)
    }
    Thread.sleep(forTimeInterval: 0.2)
    let verified = try snapshot()
    guard verified.defaultUIDs == saved.defaultUIDs else { throw Failure("Default-device restoration mismatch") }
    for device in saved.devices {
        guard let active = verified.devices.first(where: { $0.uid == device.uid }),
              abs(active.rate - device.rate) < 0.01 else { throw Failure("Saved device/rate restoration mismatch") }
    }
}

final class Recorder {
    let lock = NSLock()
    let target: Int64
    let frameBytes: UInt32 = 6
    var frames: Int64 = 0
    var done = false
    var error: String?
    var file: AudioFileID?

    init(_ target: Int64) { self.target = target }

    func receive(_ queue: AudioQueueRef, _ buffer: AudioQueueBufferRef) {
        lock.lock()
        defer { lock.unlock() }
        if done { return }
        var count = UInt32(min(Int64(buffer.pointee.mAudioDataByteSize / frameBytes), target - frames))
        guard let file else { done = true; error = "Recording file unavailable"; return }
        let status = AudioFileWritePackets(file, false, count * frameBytes, nil,
                                           frames, &count, buffer.pointee.mAudioData)
        if status != noErr { done = true; error = "PCM write failed (OSStatus \(status))"; return }
        frames += Int64(count)
        done = frames >= target
        if !done {
            let result = AudioQueueEnqueueBuffer(queue, buffer, 0, nil)
            if result != noErr { done = true; error = "Input buffer failed (OSStatus \(result))" }
        }
    }

    func stop(_ message: String? = nil) {
        lock.lock(); defer { lock.unlock() }
        done = true
        if let message { error = message }
    }

    func finished() -> Bool {
        lock.lock(); defer { lock.unlock() }
        return done
    }

    func capture(_ path: String, _ device: String, _ rate: Double, _ seconds: Double,
                 _ ready: String?, _ stopMarker: String?) throws {
        var format = AudioStreamBasicDescription(mSampleRate: rate, mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked,
            mBytesPerPacket: frameBytes, mFramesPerPacket: 1, mBytesPerFrame: frameBytes,
            mChannelsPerFrame: 2, mBitsPerChannel: 24, mReserved: 0)
        try checked(AudioFileCreateWithURL(URL(fileURLWithPath: path) as CFURL, kAudioFileWAVEType,
                                          &format, AudioFileFlags(rawValue: 0), &file), "Create WAV")
        defer { if let file { AudioFileClose(file) } }
        var queue: AudioQueueRef?
        let callback: AudioQueueInputCallback = { user, queue, buffer, _, _, _ in
            if let user { Unmanaged<Recorder>.fromOpaque(user).takeUnretainedValue().receive(queue, buffer) }
        }
        try checked(AudioQueueNewInput(&format, callback, Unmanaged.passUnretained(self).toOpaque(),
                                       nil, nil, 0, &queue), "Create input queue")
        guard let queue else { throw Failure("Input queue unavailable") }
        defer { AudioQueueStop(queue, true); AudioQueueDispose(queue, true) }
        var uid = device as CFString
        let selected = withUnsafePointer(to: &uid) {
            AudioQueueSetProperty(queue, kAudioQueueProperty_CurrentDevice, $0,
                                  UInt32(MemoryLayout<CFString>.size))
        }
        try checked(selected, "Select recording device")
        for _ in 0..<3 {
            var buffer: AudioQueueBufferRef?
            try checked(AudioQueueAllocateBuffer(queue, UInt32(rate / 10) * frameBytes, &buffer), "Allocate input buffer")
            guard let buffer else { throw Failure("Input buffer unavailable") }
            try checked(AudioQueueEnqueueBuffer(queue, buffer, 0, nil), "Arm input buffer")
        }
        let sources = [SIGINT, SIGTERM].map { code -> DispatchSourceSignal in
            signal(code, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: code, queue: .global())
            source.setEventHandler { self.stop() }
            source.resume()
            return source
        }
        defer { sources.forEach { $0.cancel() } }
        try checked(AudioQueueStart(queue, nil), "Start capture")
        if let ready { try Data().write(to: URL(fileURLWithPath: ready), options: .withoutOverwriting) }
        print("{\"event\":\"ready\"}")
        fflush(stdout)
        let deadline = Date().addingTimeInterval(seconds + 5)
        while !finished() {
            if let stopMarker, FileManager.default.fileExists(atPath: stopMarker) { stop() }
            if Date() > deadline { stop("Input timeout before the requested frame count") }
            Thread.sleep(forTimeInterval: 0.02)
        }
        try checked(AudioQueueStop(queue, true), "Stop capture")
        if let error { throw Failure(error) }
        guard frames > 0 else { throw Failure("No audio frames captured") }
        print("{\"frames\":\(frames),\"seconds\":\(Double(frames) / rate),\"sample_rate\":\(rate),\"bits\":24}")
    }
}

func main() throws {
    let args = Array(CommandLine.arguments.dropFirst())
    let help = """
    Usage:
      coreaudio list
      coreaudio save STATE.json
      coreaudio select DEVICE_ID SAMPLE_RATE
      coreaudio restore STATE.json
      coreaudio record OUTPUT.wav DEVICE_UID SAMPLE_RATE SECONDS [READY_FILE [STOP_FILE]]
    Recording is stereo 24-bit integer PCM, bounded to at most one hour.
    Save state and arm recovery before selecting BlackHole. Outputs are not overwritten.
    """
    if args.isEmpty || args == ["--help"] { print(help); return }
    switch args[0] {
    case "list" where args.count == 1:
        print(String(data: try JSONEncoder().encode(snapshot()), encoding: .utf8)!)
    case "save" where args.count == 2:
        try JSONEncoder().encode(snapshot()).write(to: URL(fileURLWithPath: args[1]), options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: args[1])
    case "restore" where args.count == 2:
        try restore(args[1]); print("Audio state restored and verified")
    case "select" where args.count == 3:
        guard let id = AudioDeviceID(args[1]), let rate = Double(args[2]), rate.isFinite, rate >= 8000,
              let device = try devices().first(where: { $0.id == id }),
              device.name.lowercased().contains("blackhole"), device.inputChannels >= 2,
              device.outputChannels >= 2 else { throw Failure("Select a valid BlackHole stereo device and rate") }
        try set(id, kAudioDevicePropertyNominalSampleRate, rate)
        try set(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyDefaultOutputDevice, id)
        try set(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyDefaultInputDevice, id)
        Thread.sleep(forTimeInterval: 0.2)
        guard abs(try number(id, kAudioDevicePropertyNominalSampleRate, Double(0)) - rate) < 0.01 else {
            throw Failure("Requested nominal sample rate was not applied")
        }
    case "record" where (5...7).contains(args.count):
        guard let rate = Double(args[3]), let seconds = Double(args[4]), rate.isFinite, seconds.isFinite,
              rate >= 8000, rate <= 192000, seconds > 0, seconds <= 3600,
              let device = try devices().first(where: { $0.uid == args[2] }),
              device.name.lowercased().contains("blackhole"), device.inputChannels >= 2,
              abs(device.rate - rate) < 0.01 else { throw Failure("Use BlackHole at its current sample rate and a bounded duration") }
        for path in [args[1]] + Array(args.dropFirst(5)) {
            if FileManager.default.fileExists(atPath: path) { throw Failure("Recording/marker path already exists") }
        }
        try Recorder(Int64((seconds * rate).rounded())).capture(args[1], args[2], rate, seconds,
            args.count >= 6 ? args[5] : nil, args.count >= 7 ? args[6] : nil)
    default:
        throw Failure(help)
    }
}

do { try main() } catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
