# -*- coding: utf-8 -*-
"""
/***************************************************************************
 *                                                                         *
 *   Overflight Contour Calculator                                         *
 *                                                                         *
 *   A QGIS plugin that calculates aircraft overflight contours and other  *
 *   metrics based on CAA CAP 1498. Written for Finavia Oyj in 2026.       *
 *   Published in 2026. Copyright (c) 2026 by Leevi Miettinen.             *
 *   Base for plugin generated with Plugin Builder.                        *
 *                                                                         *
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QLocale, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QProgressDialog
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsCoordinateTransform,
    QgsProject,
    QgsPoint,
    QgsField,
    QgsSpatialIndex,
    QgsFeatureRequest,
    QgsSettings,
    QgsWkbTypes,
    QgsMessageLog,
    QgsMapLayerProxyModel,
    Qgis
)
from PyQt5.QtCore import QVariant
import processing
import math
import os.path
from .overflight_contour_calculator_dialog import OverflightContourCalculatorDialog as OCCDialog

class OverflightContourCalculator:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QgsSettings().value('locale/userLocale', QLocale().name())[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            '{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Overflight Contour Calculator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OverflightContourCalculator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Calculate overflight count contours'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Overflight Contour Calculator'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = OCCDialog()

            # only allow vect/rast as input lyrs
            self.dlg.aircraft_track_data.setFilters(QgsMapLayerProxyModel.LineLayer)
            self.dlg.dem.setFilters(QgsMapLayerProxyModel.RasterLayer)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        if result:

            # INPUTS FROM UI

            # defualt value for log msg
            track_layer = track_alt_unit = dem_layer = dem_alt_unit = override_dem = set_obs_alt = thr_angle = alt_ceil_measure = alt_ceil = grid_size = output_type = contour_thresholds = output_proj = extent = "<NULL>"
            convert_x_to_m = {
                "m": 1,
                "ft": 0.3048,
                "mi": 1609.344,
                "km": 1000
            }
            
            track_layer = self.dlg.aircraft_track_data.currentLayer()
            if track_layer:
                # check if track data has altitude values 
                if not QgsWkbTypes.hasZ(track_layer.wkbType()):
                    QgsMessageLog.logMessage("Error: Track data is missing Z-values", "Overflight Contour Calculator", Qgis.Critical)
                    return
            track_alt_unit = self.dlg.aircraft_track_data_altitude_unit.currentText()

            override_dem = self.dlg.override_dem.isChecked()
            if override_dem:
                set_obs_alt = float(self.dlg.set_observer_altitude.value())
                obs_alt_unit = self.dlg.demobs_altitude_unit.currentText()
                # ensure value is meters
                set_obs_alt = set_obs_alt * convert_x_to_m[obs_alt_unit]
            else:
                dem_layer = self.dlg.dem.currentLayer()
                dem_alt_unit = self.dlg.demobs_altitude_unit.currentText()

            thr_angle = float(self.dlg.cone_threshold_angle.value())

            alt_ceil = float(self.dlg.altitude_ceil.value())
            alt_ceil_measure = self.dlg.altitude_ceil_measure.currentText()
            # ensure value is meters
            if "(ft" in alt_ceil_measure:
                alt_ceil = alt_ceil * convert_x_to_m['ft']
            if "AMSL" in alt_ceil_measure:
                alt_ceil_measure = "AMSL"
            else:
                alt_ceil_measure = "AGL"

            grid_size = float(self.dlg.grid_size.value())
            
            output_type = self.dlg.output_type.currentText()
            if "Contour polygons AND observer point grid" in output_type:
                output_type = "both"
            elif "Contour polygons" in output_type:
                output_type = "contours"
            else:
                output_type = "points"

            contour_thresholds = self.dlg.contour_thresholds.text()
            # ['10', '50', '100']
            contour_thresholds = contour_thresholds.replace(',', ' ').split()
            # string for GDAL "10 50 100"
            contour_thresholds = ' '.join(contour_thresholds)

            output_proj = self.dlg.output_projection.crs()
            # output_proj_epsg = output_proj.authid()
            if output_proj.isGeographic():
                QgsMessageLog.logMessage("Error: Output CRS must be projected, not geographic (degrees)", "Overflight Contour Calculator", Qgis.Critical)
                return

            extent = self.dlg.extent.outputExtent()
            # buffer extent to fix pixel shift in interpolation
            half_pixel = grid_size / 2.0
            x_min = extent.xMinimum() - half_pixel
            x_max = extent.xMaximum() + half_pixel
            y_min = extent.yMinimum() - half_pixel
            y_max = extent.yMaximum() + half_pixel
            buf_extent = f"{x_min},{x_max},{y_min},{y_max}"

            QgsMessageLog.logMessage("CALCULATION STARTED WITH THE FOLLOWING PARAMS:", "Overflight Contour Calculator", Qgis.Success)
            log_msg = ("\nTrack Layer: " + str(track_layer)
                   + "\nTrack Layer Altitude Unit: " + str(track_alt_unit)
                   + "\nDEM Layer: " + str(dem_layer)
                   + "\nDEM Layer Altitude Unit: " + str(dem_alt_unit)
                   + "\nOverride DEM With Set Observer Value: " + str(override_dem)
                   + "\nSet Observer Value: " + str(set_obs_alt)
                   + "\nCone Threshold Angle (deg): " + str(thr_angle)
                   + "\nAltitude Ceiling Measure: " + str(alt_ceil_measure)
                   + "\nAltitude Ceiling: " + str(alt_ceil)
                   + "\nGrid Size (m): " + str(grid_size)
                   + "\nOutput Type: " + str(output_type)
                   + "\nContour thresholds (≤): " + str(contour_thresholds)
                   + "\nOutput Projection: " + str(output_proj)
                   + "\nCalculation Extent: " + str(extent))
            QgsMessageLog.logMessage(log_msg, "Overflight Contour Calculator", Qgis.Info)





            # GENERATE POINT GRID WITH ALTITUDE VALUES

            # generate observer point grid
            parameters = {
                'TYPE': 0,
                'EXTENT': buf_extent,
                'HSPACING': grid_size,
                'VSPACING': grid_size,
                'HOVERLAY': 0,
                'VOVERLAY': 0,
                'CRS': output_proj,
                'OUTPUT': 'memory:'
            }
            result = processing.run("native:creategrid", parameters)
            grid_layer = result['OUTPUT']

            # use the same set alt value for all points if dem override = True
            if override_dem:
                parameters = {
                    'INPUT': grid_layer,
                    'Z_VALUE': set_obs_alt,
                    'OUTPUT': 'memory:'
                }
                result = processing.run("native:setzvalue", parameters)
                grid_with_alt = result['OUTPUT']
            # else get alt data for points from dem
            else:
                # new layer w Z coordinates
                grid_with_alt = QgsVectorLayer(f"PointZ?crs={output_proj.authid()}", "grid_with_alt", "memory")
                provider = grid_with_alt.dataProvider()
                
                new_features = []
                for feat in grid_layer.getFeatures():
                    geom = feat.geometry()
                    
                    # trans. a copy of point to dem crs
                    temp_geom = QgsGeometry(geom)
                    temp_geom.transform(QgsCoordinateTransform(output_proj, dem_layer.crs(), QgsProject.instance()))
                    sample_pt = temp_geom.asPoint()
                    
                    # sample dem, band 1 assumed
                    z_val, valid = dem_layer.dataProvider().sample(sample_pt, 1)
                    if valid:
                        z = z_val
                    else:
                        z = 0.0  # 0 if nodata or out of bounds
                    
                    # a new 3D point in target crs
                    orig_pt = geom.asPoint()
                    new_geom = QgsGeometry.fromPoint(QgsPoint(orig_pt.x(), orig_pt.y(), z))
                    
                    new_feat = QgsFeature()
                    new_feat.setGeometry(new_geom)
                    new_features.append(new_feat)

                provider.addFeatures(new_features)
                grid_with_alt.updateExtents()





                # CALCULATE THE OVERFLIGHTS

                # reproject tracks to selected crs
                parameters = {
                    'INPUT': track_layer,
                    'TARGET_CRS': output_proj,
                    'OUTPUT': 'memory:' 
                }
                result = processing.run("native:reprojectlayer", parameters)
                reprojected_tracks = result['OUTPUT']

                provider = grid_with_alt.dataProvider()

                # add OFCOUNT (overlfight) field
                if provider.fieldNameIndex("OFCOUNT") == -1:
                    provider.addAttributes([QgsField("OFCOUNT", QVariant.Type(QVariant.Int))])
                    grid_with_alt.updateFields()
                ofcount_idx = provider.fieldNameIndex("OFCOUNT")

                # max lat dist (used to limit number of calculations = faster)
                # tan_angle used later also
                tan_angle = math.tan(math.radians(thr_angle))
                max_lat_dist = alt_ceil / tan_angle
                
                # init a dict to keep track of counts in mem
                point_counts = {
                    f.id(): 0 for f in grid_with_alt.getFeatures()
                }

                # spatial index of grid points (for speed)
                index = QgsSpatialIndex(grid_with_alt)

                # iterate flight tracks
                total_tracks = reprojected_tracks   .featureCount()
                progress = QProgressDialog("Calculating Overflights...", "Cancel", 0, total_tracks, self.dlg)
                progress.setWindowTitle("Please Wait")
                progress.setWindowModality(Qt.WindowModal)
                progress.show()

                for i, track_feat in enumerate(reprojected_tracks .getFeatures()):
                    # update progress bar
                    progress.setValue(i)
                    QCoreApplication.processEvents()

                    # allow cancel
                    if progress.wasCanceled():
                        QgsMessageLog.logMessage("Calculation canceled", "Overflight Contour Calculator", Qgis.Warning)
                        return

                    track_geom = track_feat.geometry()
                    
                    # skip track if outside extent + max_lat_dist
                    search_extent = extent.buffered(max_lat_dist)
                    if not track_geom.boundingBox().intersects(search_extent):
                        continue

                    # points this track has already counted for
                    counted_for_this_track = set()
                    
                    # buffer the tracks bounding box to find points usign spatial index
                    track_bbox_buffered = track_geom.boundingBox().buffered(max_lat_dist)
                    candidate_ids = index.intersects(track_bbox_buffered)

                    # if no points found skip track                   
                    if not candidate_ids:
                        continue
                    
                    # loop through found points
                    request = QgsFeatureRequest().setFilterFids(candidate_ids)
                    for pt_feat in grid_with_alt.getFeatures(request):
                        point_id = pt_feat.id()
                        
                        # skip if point already got +1 from this track
                        if point_id in counted_for_this_track:
                            continue
                            
                        pt_geom = pt_feat.geometry()
                        
                        # 2D dist from point to track
                        dist_2d = pt_geom.distance(track_geom)
                        
                        # skip if further than max lat dist
                        if dist_2d > max_lat_dist:
                            continue
                        
                        # get closest vert index on the track to current point
                        # _ = throwaway var
                        _, vertex_index, _, _, _ = track_geom.closestVertex(pt_geom.asPoint())
                        
                        # extract actual 3D vert from track geom w index
                        closest_3d_vertex = track_geom.vertexAt(vertex_index)
                        # get only z value of vert
                        z_track = closest_3d_vertex.z()

                        # alt of point currently being porcessed
                        z_point = pt_geom.vertexAt(0).z()

                        # convert z value to m
                        z_track = z_track * convert_x_to_m[track_alt_unit]

                        # plane height above obs point
                        height_above_ground = z_track - z_point
                        
                        # plane must be above obs point
                        if height_above_ground >= 0:
                            is_below_ceiling = False
                                # AGL
                            if alt_ceil_measure == "AGL":
                                if height_above_ground <= alt_ceil:
                                    is_below_ceiling = True
                            else:
                                # AMSL
                                if z_track <= alt_ceil:
                                    is_below_ceiling = True

                            # if under ceiling, do cone math
                            if is_below_ceiling:
                                max_dist_for_point = height_above_ground / tan_angle
                                
                                if dist_2d <= max_dist_for_point:
                                    point_counts[point_id] += 1
                                    counted_for_this_track.add(point_id)
            
                # close progress bar
                progress.setValue(total_tracks)

                # write final counts to points layer in one go
                attribute_updates = {}
                for point_id, count in point_counts.items():
                    attribute_updates[point_id] = {ofcount_idx: count}

                provider.changeAttributeValues(attribute_updates)

                # add grid to project if wanted
                if output_type in ["both", "points"]:
                    grid_with_alt.setName("OCC_obs_pt_grid")
                    QgsProject.instance().addMapLayer(grid_with_alt)





            # CALCULATE CONTOURS FROM POINT GRID (if wanted)

            if output_type in ["both", "contours"]:
                # rasterize point grid
                rasterize_params = {
                    'INPUT': grid_with_alt,
                    'FIELD': 'OFCOUNT',
                    'UNITS': 1, # 1=georeferenced units
                    'WIDTH': grid_size,
                    'HEIGHT': grid_size,
                    'EXTENT': extent,
                    'INIT': 0,
                    'NODATA': -9999,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                }
                raster_result = processing.run("gdal:rasterize", rasterize_params)
                raw_raster = raster_result['OUTPUT']

                # soften grid
                soft_resolution = grid_size / 2.0  
                warp_params = {
                    'INPUT': raw_raster,
                    'TARGET_RESOLUTION': soft_resolution, 
                    'RESAMPLING': 1, # 1=bilinear
                    'NODATA': -9999,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                }
                warp_result = processing.run("gdal:warpreproject", warp_params)
                safe_raster = warp_result['OUTPUT']

                lowest_valid_level = float(contour_thresholds.split()[0])

                # generate contour rings
                contour_params = {
                    'INPUT': safe_raster,
                    'BAND': 1,
                    'INTERVAL': 9999,
                    'FIELD_NAME_MIN': 'MIN_COUNT',
                    'FIELD_NAME_MAX': 'MAX_COUNT',
                    'IGNORE_NODATA': False,
                    'EXTRA': f'-fl {contour_thresholds}', 
                    'OUTPUT': 'TEMPORARY_OUTPUT' 
                }
                contour_result = processing.run("gdal:contour_polygon", contour_params)
                raw_rings = contour_result['OUTPUT']

                # remove artifacts if any exist
                min_area = (grid_size ** 2) * 2 
                filter_params = {
                    'INPUT': raw_rings,
                    'EXPRESSION': f'"MIN_COUNT" >= {lowest_valid_level} AND $area > {min_area}',
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                }
                filter_result = processing.run("native:extractbyexpression", filter_params)
                
                # load polygons to project
                contour_layer = filter_result['OUTPUT']
                lyr_suffix = contour_thresholds.replace(' ', '_')
                contour_layer.setName(f"OCC_contours_{lyr_suffix}")
                QgsProject.instance().addMapLayer(contour_layer)