"""Media file classes for extracting EXIF/XML metadata and GPS coordinates."""

from xml.dom import minidom
import re
import PIL
from PIL import Image
from PIL.ExifTags import TAGS
import pillow_heif
import piexif

from .exiftool_runner import run_exiftool_json


class HEICFile:
    """Class for .heic files."""

    def __init__(self, mediafile_location_disk, logger):
        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        logger.debug('Run method: get_exif_from_heic')
        self.heic_metadata = self.get_exif_from_heic(mediafile_location_disk, logger)
        logger.debug('Run method: mediafile_creationdate')
        self.mediafile_creationdate = self.get_creationdate_from_heic(self.heic_metadata) \
            if self.heic_metadata else None
        logger.debug('Run method: get_geotagging_from_heic')
        self.mediafile_geodata = self.get_geotagging_from_heic(self.heic_metadata) \
            if self.heic_metadata else None
        logger.debug('Run method: get_geocoordinates_from_heic')
        self.mediafile_geolocation = self.get_geocoordinates_from_heic(self.mediafile_geodata) \
            if self.mediafile_geodata else None

    def convert_heic_geocoordinate_to_decimals(self, geo_degrees, geo_minutes,
                                               geo_seconds, reference):
        geocoordinates_in_decimals = float(geo_degrees) + \
            float(geo_minutes) / 60 + \
            float(geo_seconds) / (60 * 60)
        if reference in ['S', 'W', b'S', b'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def get_exif_from_heic(self, mediafile_location_disk, logger):
        logger.debug('Supported: %s', pillow_heif.is_supported(mediafile_location_disk))
        logger.debug('Mime: %s', pillow_heif.get_file_mimetype(mediafile_location_disk))
        try:
            heic_file = pillow_heif.open_heif(mediafile_location_disk, convert_hdr_to_8bit=False)
        except PIL.UnidentifiedImageError:
            logger.warning("Unidentified Image Error for %s", mediafile_location_disk)
            return None
        except PIL.Image.DecompressionBombError:
            logger.warning("Decompression Bomb Error for %s", mediafile_location_disk)
            return None
        except AttributeError:
            return None
        exif_dict = None
        for image in heic_file:
            if image.info.get("exif", None):
                exif_dict = piexif.load(image.info["exif"], key_is_name=True)
        return exif_dict

    def get_geotagging_from_heic(self, heif_exif_dict):
        if not heif_exif_dict:
            return None
        if "GPS" in heif_exif_dict.keys():
            return heif_exif_dict['GPS']
        return None

    def get_geocoordinates_from_heic(self, gpscoordinates_from_heic):
        if gpscoordinates_from_heic is None or gpscoordinates_from_heic == {}:
            return None
        gps_lat_degrees = gpscoordinates_from_heic['GPSLatitude'][0][0] \
            / float(gpscoordinates_from_heic['GPSLatitude'][0][1])
        gps_lat_minutes = gpscoordinates_from_heic['GPSLatitude'][1][0] \
            / float(gpscoordinates_from_heic['GPSLatitude'][1][1])
        gps_lat_seconds = gpscoordinates_from_heic['GPSLatitude'][2][0] \
            / float(gpscoordinates_from_heic['GPSLatitude'][2][1])
        gps_lat_ref = gpscoordinates_from_heic['GPSLatitudeRef']
        gps_long_degrees = gpscoordinates_from_heic['GPSLongitude'][0][0] \
            / float(gpscoordinates_from_heic['GPSLongitude'][0][1])
        gps_long_minutes = gpscoordinates_from_heic['GPSLongitude'][1][0] \
            / float(gpscoordinates_from_heic['GPSLongitude'][1][1])
        gps_long_seconds = gpscoordinates_from_heic['GPSLongitude'][2][0] \
            / float(gpscoordinates_from_heic['GPSLongitude'][2][1])
        gps_long_ref = gpscoordinates_from_heic['GPSLongitudeRef']

        if "GPSAltitude" in gpscoordinates_from_heic.keys():
            gps_altitude = gpscoordinates_from_heic['GPSAltitude']
        else:
            gps_altitude = (0, 1)

        if "GPSAltitudeRef" in gpscoordinates_from_heic.keys():
            gps_alt_ref = gpscoordinates_from_heic['GPSAltitudeRef']
        else:
            gps_alt_ref = 0

        gps_lat_decimals = self.convert_heic_geocoordinate_to_decimals(
            gps_lat_degrees, gps_lat_minutes, gps_lat_seconds, gps_lat_ref)
        gps_long_decimals = self.convert_heic_geocoordinate_to_decimals(
            gps_long_degrees, gps_long_minutes, gps_long_seconds, gps_long_ref)

        if gps_alt_ref == 0:
            gps_alt_decimals = float(gps_altitude[0]) / float(gps_altitude[1])
        elif gps_alt_ref == 1:
            gps_alt_decimals = (float(gps_altitude[0]) / float(gps_altitude[1])) * -1

        gps_alt_decimals = (float(gps_altitude[0]) / float(gps_altitude[1]))
        return gps_lat_decimals, gps_long_decimals, gps_alt_decimals

    def get_creationdate_from_heic(self, heif_exif_dict):
        if heif_exif_dict and heif_exif_dict.get('0th') is not None \
                and "DateTime" in heif_exif_dict['0th'].keys():
            return heif_exif_dict['0th']["DateTime"].decode('UTF-8')
        return None


class MP4XMLFile:
    """Class for XML files accompanying MP4 files."""

    def __init__(self, mediafile_location_disk, logger):
        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        logger.debug("Run method: get_metadata_from_xml")
        xml_metadata = self.get_metadata_from_xml(mediafile_location_disk, logger)
        logger.debug("Run method: get_creationdate")
        self.mediafile_creationdate = self.get_creationdate(xml_metadata, logger) \
            if xml_metadata else None
        logger.debug("Run method: get_geocoordinates_from_metadata")
        self.mediafile_geolocation = self.get_geocoordinates_from_metadata(xml_metadata, logger) \
            if xml_metadata else None

    def convert_geocoordinate_to_decimals(self, geocoordinate_in_degrees, reference):
        degree, minute, second = re.split(':', geocoordinate_in_degrees)
        geocoordinates_in_decimals = float(degree) + float(minute) / 60 + float(second) / (60 * 60)
        if reference in ['S', 'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def get_metadata_from_xml(self, mediafile_location_disk, logger):
        try:
            return minidom.parse(str(mediafile_location_disk))
        except Exception as exc:
            logger.warning("Could not parse XML %s: %s", mediafile_location_disk, exc)
            return None

    def get_creationdate(self, video_metadata, logger):
        video_creationdate = None
        video_creationdates = video_metadata.getElementsByTagName('CreationDate')
        for video_creationdate_item in video_creationdates:
            video_creationdate = video_creationdate_item.attributes['value'].value
        logger.debug("video_creationdate: %s", video_creationdate)
        return video_creationdate

    def get_geocoordinates_from_metadata(self, video_metadata, logger):
        altitude_direction = 0
        gpscoordinates_exist = None
        video_latitude = None
        video_longitude = None
        video_altitude = None
        video_latituderef = None
        video_longituderef = None
        video_geolocation = None
        video_metadata_items = video_metadata.getElementsByTagName('Item')
        count_latitude_elements = 0
        for video_metadata_element in video_metadata_items:
            name = video_metadata_element.attributes['name'].value
            value = video_metadata_element.attributes['value'].value
            if name == "AltitudeRef":
                altitude_direction = int(value)
            elif name == "Latitude":
                count_latitude_elements += 1
                gpscoordinates_exist = True
                video_latitude = value
            elif name == "LatitudeRef":
                video_latituderef = value
            elif name == "Longitude":
                video_longitude = value
            elif name == "LongitudeRef":
                video_longituderef = value
            elif name == "Altitude":
                video_altitude = value

        if count_latitude_elements == 0:
            gpscoordinates_exist = False

        if gpscoordinates_exist:
            latdecimal = self.convert_geocoordinate_to_decimals(video_latitude, video_latituderef)
            longdecimal = self.convert_geocoordinate_to_decimals(video_longitude, video_longituderef)
            if video_altitude is None:
                video_altitude = 0
            if altitude_direction == 0:
                video_altitude_float = float(video_altitude)
            elif altitude_direction == 1:
                video_altitude_float = -float(video_altitude)
            else:
                video_altitude_float = 0
            video_geolocation = (latdecimal, longdecimal, video_altitude_float)
            logger.debug("geolocation: %s", video_geolocation)
            return video_geolocation
        return None


class JpegFile:
    """Class for .jpg / .jpeg files."""

    def __init__(self, mediafile_location_disk, logger):
        self.geocoordinate_in_degrees = None
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug('mediafile_location_disk: %s', mediafile_location_disk)
        logger.debug('Run JpegFile method: get_exif_from_jpeg')
        self.mediafile_metadata = self.get_exif_from_jpeg(mediafile_location_disk, logger)
        logger.debug('Run JpegFile method: get_exif_labeled')
        self.jpeg_metadata_labeled = self.get_exif_labeled(self.mediafile_metadata, logger)
        logger.debug('Run JpegFile method: mediafile_creationdate')
        self.mediafile_creationdate = self.get_creationdate_from_jpeg(self.jpeg_metadata_labeled)
        if self.jpeg_metadata_labeled is not None and 'GPSInfo' in self.jpeg_metadata_labeled:
            logger.debug('Run JpegFile method: get_geocoordinates_from_jpeg')
            self.mediafile_geolocation = self.get_geocoordinates_from_jpeg(
                self.jpeg_metadata_labeled)
        else:
            self.mediafile_geolocation = None

    def convert_exif_geocoordinate_to_decimals(self, geocoordinate_in_degrees, reference):
        geocoordinates_in_decimals = float(geocoordinate_in_degrees[0]) + \
            float(geocoordinate_in_degrees[1]) / 60 + \
            float(geocoordinate_in_degrees[2]) / (60 * 60)
        if reference in ['S', 'W', b'S', b'W']:
            geocoordinates_in_decimals = geocoordinates_in_decimals * -1
        return geocoordinates_in_decimals

    def get_exif_from_jpeg(self, mediafile_location_disk, logger):
        logger.debug('JpegFile Method: get_exif_from_jpeg')
        try:
            image = Image.open(mediafile_location_disk)
            image.verify()
            return image._getexif()
        except PIL.UnidentifiedImageError:
            logger.warning("Unidentified Image Error for %s", mediafile_location_disk)
            return None
        except PIL.Image.DecompressionBombError:
            logger.warning("Decompression Bomb Error for %s", mediafile_location_disk)
            return None
        except AttributeError:
            return None

    def get_exif_labeled(self, jpeg_metadata, logger):
        logger.debug('JpegFile Method: get_exif_labeled')
        if jpeg_metadata is None:
            return None
        labeled = {}
        for (key, val) in jpeg_metadata.items():
            labeled[TAGS.get(key)] = val
        return labeled

    def get_creationdate_from_jpeg(self, jpeg_metadata_labeled):
        if jpeg_metadata_labeled is not None and "DateTime" in jpeg_metadata_labeled.keys():
            return jpeg_metadata_labeled["DateTime"]
        return None

    def get_geocoordinates_from_jpeg(self, jpeg_metadata_labeled):
        try:
            jpggeotags = jpeg_metadata_labeled['GPSInfo']
            photo_latitude = self.convert_exif_geocoordinate_to_decimals(
                jpggeotags['GPSLatitude'], jpggeotags['GPSLatitudeRef'])
            photo_longitude = self.convert_exif_geocoordinate_to_decimals(
                jpggeotags['GPSLongitude'], jpggeotags['GPSLongitudeRef'])
            if jpggeotags["GPSAltitudeRef"] == b'\x00':
                photo_altitude = float(jpggeotags["GPSAltitude"])
            else:
                photo_altitude = -float(jpggeotags["GPSAltitude"])
            return photo_latitude, photo_longitude, photo_altitude
        except Exception:
            return None


class VideoFile:
    """Class for video files (.mp4, .mts) — uses exiftool to extract embedded GPS.

    Handles AVCHD .MTS (Sony actioncam, camcorders) where GPS is in the MPEG-TS
    stream, GoPro .MP4 (GPMF telemetry track), and Apple/DJI .MP4 (©xyz atom).
    Returns None if no valid GPS sample is found or exiftool is unavailable.
    """

    def __init__(self, mediafile_location_disk, logger):
        self.mediafile_location_disk = mediafile_location_disk
        logger.debug("VideoFile mediafile_location_disk: %s", mediafile_location_disk)
        metadata = self._run_exiftool(mediafile_location_disk, logger)
        self.mediafile_creationdate = self._pick_creationdate(metadata)
        self.mediafile_geolocation = self._pick_geolocation(metadata)

    @staticmethod
    def _run_exiftool(path, logger):
        # -ee  walks embedded streams (required for AVCHD/GoPro telemetry)
        # -n   emits numeric values (decimal degrees, signed via Composite)
        # -j   JSON output
        # -G1  qualifies tags by group (so we can tell GPS: from Track4:)
        # -api largefilesupport=1   needed for big video files
        result = run_exiftool_json([
            "-ee", "-n", "-j", "-G1", "-api", "largefilesupport=1",
            "-Composite:GPSLatitude", "-Composite:GPSLongitude",
            "-Composite:GPSAltitude", "-GPS:GPSAltitude", "-Track4:GPSAltitude",
            "-GPS:GPSStatus",
            "-Composite:GPSDateTime", "-QuickTime:CreateDate", "-CreateDate",
            str(path),
        ])
        if not result:
            logger.debug("exiftool returned nothing for %s", path)
            return None
        return result[0] if isinstance(result, list) and result else None

    @staticmethod
    def _pick_geolocation(metadata):
        if not metadata:
            return None
        lat = metadata.get("Composite:GPSLatitude")
        lon = metadata.get("Composite:GPSLongitude")
        if lat is None or lon is None:
            return None
        # AVCHD records GPSStatus="V" for void/no-fix samples; skip those.
        if metadata.get("GPS:GPSStatus") == "V":
            return None
        alt = (metadata.get("Composite:GPSAltitude")
               or metadata.get("GPS:GPSAltitude")
               or metadata.get("Track4:GPSAltitude") or 0.0)
        try:
            return float(lat), float(lon), float(alt)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pick_creationdate(metadata):
        if not metadata:
            return None
        return (metadata.get("Composite:GPSDateTime")
                or metadata.get("QuickTime:CreateDate")
                or metadata.get("CreateDate"))
