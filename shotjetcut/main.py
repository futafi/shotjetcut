import sys
import argparse
from . import shotcut
from . import timeline

def main():
    # command: shotjetcut -i INPUTFILE.{mp4, mkv or etc} -o OUTPUTFILE.mlt -a audio_tracks  --opt key=value
    # -i: required, if not error
    # -o: optional
    # -a: optional default=[1,2]
    # --opt: optional
    parser = argparse.ArgumentParser(
        description="shotjetcut: create shotcut mlt file from video file",
        epilog="example: shotjetcut -i input.mp4 -o output.mlt -a 1 2 --opt aggressiveness=2 frame_duration=30 padding_duration=0.1 merge_threshold=0.15",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-i", "--input", help="input video file", default=None)
    parser.add_argument("-o", "--output", help="output mlt file", default=None)
    parser.add_argument("-a", "--audio_tracks", help="audio tracks", nargs="*", default=[1,2])
    parser.add_argument("--opt", help="options", nargs="*", default={})
    args = parser.parse_args()

    if args.input is None:
        print("input file is required")
        sys.exit(1)
    
    if args.output is None:
        args.output = f"{args.input}.mlt"

    a_tracks = []
    for a in args.audio_tracks:
        try:
            a_tracks.append(int(a))
        except ValueError:
            print("audio_tracks must be integer")
            sys.exit(1)
    
    video = timeline.process_video(args.input, audio_tracks=a_tracks, **args.opt)
    shotcut.shotcut_write_mlt(args.output, tl=video, audio_tracks=a_tracks, **args.opt)


if __name__ == "__main__":
    main()