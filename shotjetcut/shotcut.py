import xml.etree.ElementTree as ET
from . import timeline
from . import func


def shotcut_write_mlt(output: str, tl: timeline.Video, audio_tracks: list, **kwargs):
    video = tl
    mlt = ET.Element(
        "mlt",
        attrib={
            "LC_NUMERIC": "C",
            "version": "7.9.0",
            "title": "Shotcut version 22.09.23",
            "producer": "main_bin",
        },
    )
    width, height = video.res
    num, den = func.aspect_ratio(width, height)
    tb = video.tb
    ET.SubElement(
        mlt,
        "profile",
        attrib={
            "description": "automatic",
            "width": f"{width}",
            "height": f"{height}",
            "progressive": "1",
            "sample_aspect_num": "1",
            "sample_aspect_den": "1",
            "display_aspect_num": f"{num}",
            "display_aspect_den": f"{den}",
            "frame_rate_num": f"{tb.numerator}",
            "frame_rate_den": f"{tb.denominator}",
            "colorspace": "709",
        },
    )
    playlist_bin = ET.SubElement(mlt, "playlist", id="main_bin")
    ET.SubElement(playlist_bin, "property", name="xml_retain").text = "1"

    global_out = func.to_timecode(video.out_len() / tb)

    producer = ET.SubElement(mlt, "producer", id="bg")

    ET.SubElement(producer, "property", name="length").text = global_out
    ET.SubElement(producer, "property", name="eof").text = "pause"
    ET.SubElement(producer, "property", name="resource").text = "#000"  # background
    ET.SubElement(producer, "property", name="mlt_service").text = "color"
    ET.SubElement(producer, "property", name="mlt_image_format").text = "rgba"
    ET.SubElement(producer, "property", name="aspect_ratio").text = "1"

    playlist = ET.SubElement(mlt, "playlist", id="background")
    ET.SubElement(
        playlist,
        "entry",
        attrib={"producer": "bg", "in": "00:00:00.000", "out": global_out},
    ).text = "1"

    # video clip
    chains = 0
    producers = 0

    if video.v:
        clips = video.v[0]
    elif video.a:
        clips = video.a[0]
    else:
        clips = []

    for clip in clips:
        src = clip.src
        length = func.to_timecode((clip.offset + clip.dur) / tb)

        if clip.speed == 1:
            resource = f"./{src.path.name}"
            caption = f"{src.path.stem}"
            chain = ET.SubElement(
                mlt, "chain", attrib={"id": f"chain{chains}", "out": length}
            )
        else:
            chain = ET.SubElement(
                mlt, "producer", attrib={"id": f"producer{producers}", "out": length}
            )
            resource = f"./{src.path.name}"
            caption = f"{src.path.stem} ({clip.speed}x)"

            producers += 1

        ET.SubElement(chain, "property", name="length").text = length
        ET.SubElement(chain, "property", name="resource").text = resource

        if clip.speed != 1:
            ET.SubElement(chain, "property", name="warp_speed").text = f"{clip.speed}"
            ET.SubElement(chain, "property", name="warp_pitch").text = "1"
            ET.SubElement(chain, "property", name="mlt_service").text = "timewarp"

        ET.SubElement(chain, "property", name="caption").text = caption

        chains += 1

    main_playlist = ET.SubElement(mlt, "playlist", id="playlist0")
    ET.SubElement(main_playlist, "property", name="shotcut:video").text = "1"
    ET.SubElement(main_playlist, "property", name="shotcut:name").text = "V1"

    producers = 0
    for i, clip in enumerate(clips):
        _in = func.to_timecode(clip.offset / tb)
        _out = func.to_timecode((clip.offset + clip.dur) / tb)

        tag_name = f"chain{i}"
        if clip.speed != 1:
            tag_name = f"producer{producers}"
            producers += 1

        ET.SubElement(
            main_playlist,
            "entry",
            attrib={"producer": tag_name, "in": _in, "out": _out},
        )

    sr = video.tb  # TODO
    # audio clip
    for producers in range(1, len(audio_tracks) + 1):
        chains = 0
        clips = []
        for tmpclip in video.a[0]:
            if tmpclip.stream == audio_tracks[producers - 1]:
                clips.append(tmpclip)

        for clip in clips:
            src = clip.src
            # length = func.to_timecode((clip.offset + clip.dur) / sr)
            length = global_out  # TODO really?

            if clip.speed == 1:
                resource = f"./{src.path.name}"
                caption = f"{src.path.stem}"
                chain = ET.SubElement(
                    mlt, "chain", attrib={"id": f"chain{chains}", "out": length}
                )
            else:
                chain = ET.SubElement(
                    mlt, "producer", attrib={"id": f"producer{producers}", "out": length}
                )
                resource = f"{clip.speed}:./{src.path.name}"
                caption = f"{src.path.stem} ({clip.speed}x)"

                # producers += 1

            ET.SubElement(chain, "property", name="length").text = length
            ET.SubElement(chain, "property", name="resource").text = resource
            ET.SubElement(chain, "property", name="audio_index").text = str(clip.stream + 1)
            ET.SubElement(chain, "property", name="astream").text = str(clip.stream)
            ET.SubElement(chain, "property", name="video_index").text = "-1"
            ET.SubElement(chain, "property", name="vstream").text = "-1"

            if clip.speed != 1:
                ET.SubElement(chain, "property", name="warp_speed").text = f"{clip.speed}"
                ET.SubElement(chain, "property", name="warp_pitch").text = "1"
                ET.SubElement(chain, "property", name="mlt_service").text = "timewarp"

            ET.SubElement(chain, "property", name="caption").text = caption

            chains += 1

        main_playlist = ET.SubElement(mlt, "playlist", id="playlist{}".format(producers))
        ET.SubElement(main_playlist, "property", name="shotcut:audio").text = "1"
        ET.SubElement(main_playlist, "property", name="shotcut:name").text = "A{}".format(producers)

        # producers = 0
        # ET.SubElement(main_playlist, "blank", attrib={"length": func.to_timecode(clips[0].start / sr)}) # ODO
        ET.SubElement(main_playlist, "blank", attrib={"length": func.to_timecode(clips[0].start / sr)})  # ODO
        for i, clip in enumerate(clips):
            # _in = func.to_timecode(clip.offset / sr)
            # _out = func.to_timecode((clip.offset + clip.dur) / sr)
            _in = func.to_timecode(clip.start / sr)
            _out = func.to_timecode((clip.start + clip.dur) / sr)

            tag_name = f"chain{i}"
            if clip.speed != 1:
                tag_name = f"producer{producers}"
                producers += 1

            ET.SubElement(
                main_playlist,
                "entry",
                attrib={"producer": tag_name, "in": _in, "out": _out},
            )

            # clip clip 間に <blank length="00:00:xx.xxx"/>を入れる
            if i != len(clips) - 1:
                # _blank_length = func.to_timecode((clips[i+1].start - clip.start - clip.dur) / sr)
                # blank = ET.SubElement(main_playlist, "blank",attrib={"length": _blank_length})
                # print(_in, _out, _blank_length)
                # print(clip.start, clip.start+clip.dur, clips[i+1].start)
                blank = ET.SubElement(main_playlist, "blank", attrib={"length": func.to_timecode(clips[i + 1].start / sr - func.parse_timecode(_out))})

    # end section ?? TODO
    tractor = ET.SubElement(
        mlt,
        "tractor",
        attrib={"id": "tractor0", "in": "00:00:00.000", "out": global_out},
    )

    # write last
    ET.SubElement(tractor, "property", name="shotcut").text = "1"
    ET.SubElement(tractor, "property", name="shotcut:projectAudioChannels").text = "2"
    ET.SubElement(tractor, "track", producer="background")
    ET.SubElement(tractor, "track", producer="playlist0")
    for i in range(1, len(audio_tracks) + 1):
        ET.SubElement(tractor, "track", producer=f"playlist{i}")

    # これを入れないと、BGMトラックの音が重なってる場所が消える
    for i in range(len(audio_tracks)):
        transition = ET.SubElement(tractor, "transition", id=f"transition{i}")
        ET.SubElement(transition, "property", name="a_track").text = "0"
        ET.SubElement(transition, "property", name="b_track").text = f"{i + 2}"
        ET.SubElement(transition, "property", name="mlt_service").text = "mix"
        ET.SubElement(transition, "property", name="always_active").text = "1"
        ET.SubElement(transition, "property", name="sum").text = "1"

    tree = ET.ElementTree(mlt)

    ET.indent(tree, space="\t", level=0)

    tree.write(output, xml_declaration=True, encoding="utf-8")
