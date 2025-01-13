from __future__ import annotations

from enum import Enum
from pathlib import Path
import os
from random import choice
import shutil
import zipfile
from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram.types import Message
from amdlbot import bot, database

from amdlbot.logging import LOGGER
# from . import __version__
from gamdl.apple_music_api import AppleMusicApi
from gamdl.constants import *
from gamdl.downloader import Downloader
from gamdl.downloader_music_video import DownloaderMusicVideo
from gamdl.downloader_post import DownloaderPost
from gamdl.downloader_song import DownloaderSong
from gamdl.downloader_song_legacy import DownloaderSongLegacy
from gamdl.enums import (
    CoverFormat,
    DownloadMode,
    MusicVideoCodec,
    PostQuality,
    RemuxMode,
)
from gamdl.itunes_api import ItunesApi

from amdlbot.helpers.config import Config, countries
from amdlbot.helpers.utils import get_url_info



async def main(config: Config, url: str, message: Message, zip_file: bool = False):
    
    status_message = await message.reply_text("Starting...")
    
    cookie_path = choice([os.path.join("amdlbot/cookies", f) for f in os.listdir("amdlbot/cookies") if os.path.isfile(os.path.join("amdlbot/cookies", f))])
    country_name = countries.get(cookie_path[-6:-4].upper(), "Unknown Country")
    await status_message.edit_text(f"Using {country_name} account")
    
    if not Path(cookie_path).exists():
        await status_message.edit_text(X_NOT_FOUND_STRING.format("Cookies file", cookie_path))
        return
    apple_music_api = AppleMusicApi(
        Path(cookie_path),
        language=config.language,
    )
    itunes_api = ItunesApi(
        apple_music_api.storefront,
        apple_music_api.language,
    )
    
    url_info = get_url_info(url)
    _file_id = f"{url_info[0]}_{url_info[1]}".replace("pl.u-", "")
    downloads_folder = Path("downloads")
    output_path = downloads_folder / _file_id
    temp_path = downloads_folder / f"temp_{_file_id}"
    
    downloader = Downloader(
        apple_music_api,
        itunes_api,
        output_path,
        temp_path,
        config.wvd_path,
        config.nm3u8dlre_path,
        config.mp4decrypt_path,
        config.ffmpeg_path,
        config.mp4box_path,
        config.download_mode,
        config.remux_mode,
        config.cover_format,
        config.template_folder_album,
        config.template_folder_compilation,
        config.template_file_single_disc,
        config.template_file_multi_disc,
        config.template_folder_no_album,
        config.template_file_no_album,
        config.template_file_playlist,
        config.template_date,
        config.exclude_tags,
        config.cover_size,
        config.truncate,
    )
    downloader_song = DownloaderSong(
        downloader,
        config.codec_song,
        config.synced_lyrics_format,
    )
    downloader_song_legacy = DownloaderSongLegacy(
        downloader,
        config.codec_song,
    )
    downloader_music_video = DownloaderMusicVideo(
        downloader,
        config.codec_music_video,
    )
    downloader_post = DownloaderPost(
        downloader,
        config.quality_post,
    )
    if not config.synced_lyrics_only:
        if config.wvd_path and not config.wvd_path.exists():
            await status_message.edit_text(X_NOT_FOUND_STRING.format(".wvd file", config.wvd_path))
            return
        LOGGER(__name__).debug("Setting up CDM")
        downloader.set_cdm()
        if not downloader.ffmpeg_path_full and (
            config.remux_mode == RemuxMode.FFMPEG or config.download_mode == DownloadMode.NM3U8DLRE
        ):
            await status_message.edit_text(X_NOT_FOUND_STRING.format("ffmpeg", config.ffmpeg_path))
            return
        if not downloader.mp4box_path_full and config.remux_mode == RemuxMode.MP4BOX:
            await status_message.edit_text(X_NOT_FOUND_STRING.format("MP4Box", config.mp4box_path))
            return
        if (
            not downloader.mp4decrypt_path_full
            and config.codec_song
            not in (
                SongCodec.AAC_LEGACY,
                SongCodec.AAC_HE_LEGACY,
            )
            or (config.remux_mode == RemuxMode.MP4BOX and not downloader.mp4decrypt_path_full)
        ):
            await status_message.edit_text(X_NOT_FOUND_STRING.format("mp4decrypt", config.mp4decrypt_path))
            return
        if (
            config.download_mode == DownloadMode.NM3U8DLRE
            and not downloader.nm3u8dlre_path_full
        ):
            await status_message.edit_text(X_NOT_FOUND_STRING.format("N_m3u8DL-RE", config.nm3u8dlre_path))
            return
        if not downloader.mp4decrypt_path_full:
            await status_message.edit_text(
                X_NOT_FOUND_STRING.format("mp4decrypt", config.mp4decrypt_path)
                + ", music videos will not be downloaded"
            )
            skip_mv = True
        else:
            skip_mv = False
        if config.codec_song not in LEGACY_CODECS:
            await status_message.edit_text(
                "You have chosen a non-legacy codec. Support for non-legacy codecs are not guaranteed, "
                "as most of the songs cannot be downloaded when using non-legacy codecs."
            )
    error_count = 0
    try:
        await status_message.edit_text(f'(Checking "{url}"')
        url_info = downloader.get_url_info(url)
        download_queue = downloader.get_download_queue(url_info)
        download_queue_tracks_metadata = download_queue.tracks_metadata
    except Exception as e:
        error_count += 1
        await status_message.edit_text(
            f'Failed to check "{url}"',
        )
        return
    for download_index, track_metadata in enumerate(
        download_queue_tracks_metadata, start=1
    ):
        queue_progress = f"Track {download_index}/{len(download_queue_tracks_metadata)}"
        try:
            remuxed_path = None
            if download_queue.playlist_attributes:
                playlist_track = download_index
            else:
                playlist_track = None
            await status_message.edit_text(
                f'({queue_progress}) Downloading "{track_metadata["attributes"]["name"]}"'
            )
            if not track_metadata["attributes"].get("playParams"):
                await status_message.edit_text(
                    f"({queue_progress}) Track is not streamable, skipping"
                )
                continue
            if (
                (config.synced_lyrics_only and track_metadata["type"] != "songs")
                or (track_metadata["type"] == "music-videos" and skip_mv)
                or (
                    track_metadata["type"] == "music-videos"
                    and url_info.type == "album"
                    and not config.disable_music_video_skip
                )
            ):
                await status_message.edit_text(
                    f"({queue_progress}) Track is not downloadable with current configuration, skipping"
                )
                continue
            elif track_metadata["type"] == "songs":
                LOGGER(__name__).debug("Getting lyrics")
                lyrics = downloader_song.get_lyrics(track_metadata)
                LOGGER(__name__).debug("Getting webplayback")
                webplayback = apple_music_api.get_webplayback(track_metadata["id"])
                tags = downloader_song.get_tags(webplayback, lyrics.unsynced)
                if playlist_track:
                    tags = {
                        **tags,
                        **downloader.get_playlist_tags(
                            download_queue.playlist_attributes,
                            playlist_track,
                        ),
                    }
                final_path = downloader.get_final_path(tags, ".m4a")
                lyrics_synced_path = downloader_song.get_lyrics_synced_path(final_path)
                cover_url = downloader.get_cover_url(track_metadata)
                cover_file_extesion = downloader.get_cover_file_extension(cover_url)
                cover_path = downloader_song.get_cover_path(
                    final_path,
                    cover_file_extesion,
                )
                if config.synced_lyrics_only:
                    pass
                elif final_path.exists() and not config.overwrite:
                    await status_message.edit_text(f'({queue_progress}) Song already exists at "{final_path}", skipping')
                else:
                    LOGGER(__name__).debug("Getting stream info")
                    if config.codec_song in LEGACY_CODECS:
                        stream_info = downloader_song_legacy.get_stream_info(
                            webplayback
                        )
                        LOGGER(__name__).debug("Getting decryption key")
                        decryption_key = downloader_song_legacy.get_decryption_key(
                            stream_info.pssh, track_metadata["id"]
                        )
                    else:
                        stream_info = downloader_song.get_stream_info(track_metadata)
                        if not stream_info.stream_url or not stream_info.pssh:
                            await status_message.edit_text(
                                f"({queue_progress}) Song is not downloadable or is not"
                                " available in the chosen codec, skipping"
                            )
                            continue
                        LOGGER(__name__).debug("Getting decryption key")
                        decryption_key = downloader.get_decryption_key(
                            stream_info.pssh, track_metadata["id"]
                        )
                    encrypted_path = downloader_song.get_encrypted_path(
                        track_metadata["id"]
                    )
                    decrypted_path = downloader_song.get_decrypted_path(
                        track_metadata["id"]
                    )
                    remuxed_path = downloader_song.get_remuxed_path(
                        track_metadata["id"]
                    )
                    LOGGER(__name__).debug(f'Downloading to "{encrypted_path}"')
                    downloader.download(encrypted_path, stream_info.stream_url)
                    if config.codec_song in LEGACY_CODECS:
                        LOGGER(__name__).debug(
                            f'Decrypting/Remuxing to "{decrypted_path}"/"{remuxed_path}"'
                        )
                        downloader_song_legacy.remux(
                            encrypted_path,
                            decrypted_path,
                            remuxed_path,
                            decryption_key,
                        )
                    else:
                        LOGGER(__name__).debug(f'Decrypting to "{decrypted_path}"')
                        downloader_song.decrypt(
                            encrypted_path, decrypted_path, decryption_key
                        )
                        LOGGER(__name__).debug(f'Remuxing to "{final_path}"')
                        downloader_song.remux(
                            decrypted_path,
                            remuxed_path,
                            stream_info.codec,
                        )
                if config.no_synced_lyrics or not lyrics.synced:
                    pass
                elif lyrics_synced_path.exists() and not config.overwrite:
                    LOGGER(__name__).debug(
                        f'Synced lyrics already exists at "{lyrics_synced_path}", skipping'
                    )
                else:
                    LOGGER(__name__).debug(f'Saving synced lyrics to "{lyrics_synced_path}"')
                    downloader_song.save_lyrics_synced(
                        lyrics_synced_path, lyrics.synced
                    )
            elif track_metadata["type"] == "music-videos":
                music_video_id_alt = downloader_music_video.get_music_video_id_alt(
                    track_metadata
                )
                LOGGER(__name__).debug("Getting iTunes page")
                itunes_page = itunes_api.get_itunes_page(
                    "music-video", music_video_id_alt
                )
                if music_video_id_alt == track_metadata["id"]:
                    stream_url = downloader_music_video.get_stream_url_from_itunes_page(
                        itunes_page
                    )
                else:
                    LOGGER(__name__).debug("Getting webplayback")
                    webplayback = apple_music_api.get_webplayback(track_metadata["id"])
                    stream_url = downloader_music_video.get_stream_url_from_webplayback(
                        webplayback
                    )
                LOGGER(__name__).debug("Getting M3U8 data")
                m3u8_data = downloader_music_video.get_m3u8_master_data(stream_url)
                tags = downloader_music_video.get_tags(
                    music_video_id_alt,
                    itunes_page,
                    track_metadata,
                )
                if playlist_track:
                    tags = {
                        **tags,
                        **downloader.get_playlist_tags(
                            download_queue.playlist_attributes,
                            playlist_track,
                        ),
                    }
                final_path = downloader.get_final_path(tags, ".m4v")
                cover_url = downloader.get_cover_url(track_metadata)
                cover_file_extesion = downloader.get_cover_file_extension(cover_url)
                cover_path = downloader_music_video.get_cover_path(
                    final_path,
                    cover_file_extesion,
                )
                if final_path.exists() and not config.overwrite:
                    await status_message.edit_text(f'({queue_progress}) Music video already exists at "{final_path}", skipping')
                else:
                    LOGGER(__name__).debug("Getting stream info")
                    stream_info_video, stream_info_audio = (
                        downloader_music_video.get_stream_info_video(m3u8_data),
                        downloader_music_video.get_stream_info_audio(m3u8_data),
                    )
                    decryption_key_video = downloader.get_decryption_key(
                        stream_info_video.pssh, track_metadata["id"]
                    )
                    decryption_key_audio = downloader.get_decryption_key(
                        stream_info_audio.pssh, track_metadata["id"]
                    )
                    encrypted_path_video = (
                        downloader_music_video.get_encrypted_path_video(
                            track_metadata["id"]
                        )
                    )
                    encrypted_path_audio = (
                        downloader_music_video.get_encrypted_path_audio(
                            track_metadata["id"]
                        )
                    )
                    decrypted_path_video = (
                        downloader_music_video.get_decrypted_path_video(
                            track_metadata["id"]
                        )
                    )
                    decrypted_path_audio = (
                        downloader_music_video.get_decrypted_path_audio(
                            track_metadata["id"]
                        )
                    )
                    remuxed_path = downloader_music_video.get_remuxed_path(
                        track_metadata["id"]
                    )
                    LOGGER(__name__).debug(f'Downloading video to "{encrypted_path_video}"')
                    downloader.download(
                        encrypted_path_video, stream_info_video.stream_url
                    )
                    LOGGER(__name__).debug(f'Downloading audio to "{encrypted_path_audio}"')
                    downloader.download(
                        encrypted_path_audio, stream_info_audio.stream_url
                    )
                    LOGGER(__name__).debug(f'Decrypting video to "{decrypted_path_video}"')
                    downloader_music_video.decrypt(
                        encrypted_path_video,
                        decryption_key_video,
                        decrypted_path_video,
                    )
                    LOGGER(__name__).debug(f'Decrypting audio to "{decrypted_path_audio}"')
                    downloader_music_video.decrypt(
                        encrypted_path_audio,
                        decryption_key_audio,
                        decrypted_path_audio,
                    )
                    LOGGER(__name__).debug(f'Remuxing to "{remuxed_path}"')
                    downloader_music_video.remux(
                        decrypted_path_video,
                        decrypted_path_audio,
                        remuxed_path,
                        stream_info_video.codec,
                        stream_info_audio.codec,
                    )
            elif track_metadata["type"] == "uploaded-videos":
                stream_url = downloader_post.get_stream_url(track_metadata)
                tags = downloader_post.get_tags(track_metadata)
                final_path = downloader.get_final_path(tags, ".m4v")
                cover_url = downloader.get_cover_url(track_metadata)
                cover_file_extesion = downloader.get_cover_file_extension(cover_url)
                cover_path = downloader_music_video.get_cover_path(
                    final_path,
                    cover_file_extesion,
                )
                if final_path.exists() and not config.overwrite:
                    await status_message.edit_text(f'({queue_progress}) Post video already exists at "{final_path}", skipping')
                else:
                    remuxed_path = downloader_post.get_post_temp_path(
                        track_metadata["id"]
                    )
                    LOGGER(__name__).debug(f'Downloading to "{remuxed_path}"')
                    downloader.download_ytdlp(remuxed_path, stream_url)
            if config.synced_lyrics_only or not config.save_cover:
                pass
            elif cover_path.exists() and not config.overwrite:
                LOGGER(__name__).debug(f'Cover already exists at "{cover_path}", skipping')
            else:
                LOGGER(__name__).debug(f'Saving cover to "{cover_path}"')
                downloader.save_cover(cover_path, cover_url)
            if remuxed_path:
                LOGGER(__name__).debug("Applying tags")
                downloader.apply_tags(remuxed_path, tags, cover_url)
                LOGGER(__name__).debug(f'Moving to "{final_path}"')
                downloader.move_to_output_path(remuxed_path, final_path)
            if (
                not config.synced_lyrics_only
                and config.save_playlist
                and download_queue.playlist_attributes
            ):
                playlist_file_path = downloader.get_playlist_file_path(tags)
                LOGGER(__name__).debug(f'Updating M3U8 playlist from "{playlist_file_path}"')
                downloader.update_playlist_file(
                    playlist_file_path,
                    final_path,
                    playlist_track,
                )
        except Exception as e:
            error_count += 1
            await status_message.edit_text(
                f'({queue_progress}) Failed to download "{track_metadata["attributes"]["name"]}"',
            )
        finally:
            if temp_path.exists():
                LOGGER(__name__).debug(f'Cleaning up "{temp_path}"')
                downloader.cleanup_temp_path()
    if zip_file:
        zip_output_path = downloads_folder / f"{_file_id}.zip"
        #await status_message.edit_text(f'Creating zip file at "{zip_output_path}"')
        await status_message.edit_text("Creating zip file...")
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, _, files in os.walk(output_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, output_path))
        shutil.rmtree(output_path)
    await status_message.edit_text(f"Done with({error_count} error(s))")
    await status_message.delete()
    return _file_id

LOGGER(__name__).info("Apple Muisc Module loaded!")