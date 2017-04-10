"""
********************************************************************************
* Name: ColorRampGenerator
* Author: Nathan Swain
* Created On: July 21, 2014
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
"""

import math
import xml.etree.ElementTree as ET


class ColorRampEnum(object):
    """
    Enumerated list of default color ramps
    """
    COLOR_RAMP_HUE = 0
    COLOR_RAMP_TERRAIN = 1
    COLOR_RAMP_AQUA = 2


class MappedColorRamp(object):
    """
    Object containing a mapped color ramp object
    """
    R = 0
    G = 1
    B = 2

    MAX_HEX_DECIMAL = 255

    def __init__(self, colorRamp, slope, intercept, min, max, alpha=1.0):
        self.colorRamp = colorRamp
        self.slope = slope
        self.intercept = intercept
        self.min = min
        self.max = max
        self.alpha = alpha
        self.vrgbaList = []

        if self.min != self.max:
            for index in range(len(self.colorRamp)):
                rampIndex = len(self.colorRamp) - index - 1
                valueForIndex = (rampIndex - self.intercept) / self.slope
                rgb = self.colorRamp[rampIndex]
                self.vrgbaList.append('{0} {1} {2} {3} {4}'.format(valueForIndex, rgb[0], rgb[1], rgb[2], int(alpha * 255)))
        else:
            valueForIndex = self.max
            rgb = self.colorRamp[0]
            self.vrgbaList.append('{0} {1} {2} {3} {4}'.format(valueForIndex, rgb[0], rgb[1], rgb[2], int(alpha * 255)))

        # Add a line for the no-data values (nv)
        self.vrgbaList.append('nv 0 0 0 0')

    def __repr__(self):
        return '<MappedColorRamp Slope={0}, Intercept={1}, MinValue={2}, MaxValue={3}, Alpha={4}>'.format(self.slope,
                                                                                                          self.intercept,
                                                                                                          self.min,
                                                                                                          self.max,
                                                                                                          self.alpha)

    def getColorForIndex(self, index):
        """
        Return color for given index
        :rtype: tuple of RGB integer values
        """
        return self.colorRamp[index]

    def getColorForValue(self, value):
        """
        Return a color tuple give a value within the range of mapped values
        :param value: Lookup value
        :rtype: tuple of RGB integer values
        """
        rampIndex = 0

        if value >= self.min and value <= self.max:
            rampIndex = self.getIndexForValue(value)

        elif value > self.max:
            rampIndex = -1

        elif value < self.min:
            rampIndex = 0

        return self.getColorForIndex(rampIndex)

    def getIndexForValue(self, value):
        """
        Return the ramp index for the given value
        :param value: Lookup value
        :rtype: int
        """
        return math.trunc(self.slope * float(value) + self.intercept)

    def getAlphaAsInteger(self):
        """
        Return the transparency (alpha) as a hex decimal
        """
        return int(self.alpha * self.MAX_HEX_DECIMAL)

    def getPostGisColorRampString(self):
        # Join strings in list to create ramp
        return '\n'.join(self.vrgbaList)

    def getAsVrgbaList(self):
        """
        Return ramp as a list of value RGBA strings (vrgba)
        :rtype: str
        """
        return self.vrgbaList

    def getColorMapAsContinuousSLD(self, nodata=-9999):
        """
        Return the mapped color ramp as a
        :rtype: str
        """
        colorMap = ET.Element('ColorMap', type='interval')

        # Add a line for the no-data values (nv)
        ET.SubElement(colorMap, 'ColorMapEntry', color='#000000', quantity=str(nodata), label='NoData', opacity='0.0')

        def get_label_formatter(value):
            label_tag="{label:.0f}"
            if abs(value) < 0.01 and value != 0:
                label_tag = "{label:.2E}"
            elif abs(value) < 10:
                label_tag="{label:.2f}"
            elif abs(value) < 99:
                label_tag="{label:.1f}"
            return label_tag

        if self.min != self.max and self.slope > 0:
            for rampIndex in range(len(self.colorRamp)):
                valueForIndex = (rampIndex - self.intercept) / self.slope
                red, green, blue = self.colorRamp[rampIndex]
                hexRGB = '#%02X%02X%02X' % (red,
                                            green,
                                            blue)

                label_tag = get_label_formatter(valueForIndex)
                ET.SubElement(colorMap, 'ColorMapEntry', color=hexRGB,
                              quantity=str(valueForIndex),
                              label=label_tag.format(label=valueForIndex),
                              opacity=str(self.alpha))
        else:
            valueForIndex = self.max
            red, green, blue = self.colorRamp[0]
            hexRGB = '#%02X%02X%02X' % (red,
                                        green,
                                        blue)
            label_tag = get_label_formatter(valueForIndex)
            ET.SubElement(colorMap, 'ColorMapEntry', color=hexRGB,
                          quantity=str(valueForIndex),
                          label=label_tag.format(label=valueForIndex),
                          opacity=str(self.alpha))


        return ET.tostring(colorMap)

    def getColorMapAsDiscreetSLD(self, uniqueValues, nodata=-9999):
        """
        Create the color map SLD format from a list of values.
        :rtype: str
        """
        colorMap = ET.Element('ColorMap', type='values')
        # Add a line for the no-data values (nv)
        ET.SubElement(colorMap, 'ColorMapEntry', color='#000000', quantity=str(nodata), label='NoData', opacity='0.0')

        for value in uniqueValues:
            red, green, blue = self.getColorForValue(value)
            hexRGB = '#%02X%02X%02X' % (red,
                                        green,
                                        blue)

            ET.SubElement(colorMap, 'ColorMapEntry', color=hexRGB, quantity=str(value), label=str(value), opacity=str(self.alpha))

        return ET.tostring(colorMap)



class ColorRampGenerator(object):
    """
    An instance of the ColorRampGenerator can be used to generate and manipulate color ramps in MapKit
    """

    # Class variables
    LINE_COLOR = 'FF000000'
    LINE_WIDTH = 1
    MAX_HEX_DECIMAL = 255
    NO_DATA_VALUE_MIN = float(-1.0)
    NO_DATA_VALUE_MAX = float(0.0)

    @classmethod
    def generateDefaultColorRamp(cls, colorRampEnum):
        """
        Returns the color ramp as a list of RGB tuples
        :param colorRampEnum: One of the
        """
        hue = [(255, 0, 255), (231, 0, 255), (208, 0, 255), (185, 0, 255), (162, 0, 255), (139, 0, 255), (115, 0, 255), (92, 0, 255), (69, 0, 255), (46, 0, 255), (23, 0, 255),        # magenta to blue
                   (0, 0, 255), (0, 23, 255), (0, 46, 255), (0, 69, 255), (0, 92, 255), (0, 115, 255), (0, 139, 255), (0, 162, 255), (0, 185, 255), (0, 208, 255), (0, 231, 255),          # blue to cyan
                   (0, 255, 255), (0, 255, 231), (0, 255, 208), (0, 255, 185), (0, 255, 162), (0, 255, 139), (0, 255, 115), (0, 255, 92), (0, 255, 69), (0, 255, 46), (0, 255, 23),        # cyan to green
                   (0, 255, 0), (23, 255, 0), (46, 255, 0), (69, 255, 0), (92, 255, 0), (115, 255, 0), (139, 255, 0), (162, 255, 0), (185, 255, 0), (208, 255, 0), (231, 255, 0),          # green to yellow
                   (255, 255, 0), (255, 243, 0), (255, 231, 0), (255, 220, 0), (255, 208, 0), (255, 197, 0), (255, 185, 0), (255, 174, 0), (255, 162, 0), (255, 151, 0), (255, 139, 0),    # yellow to orange
                   (255, 128, 0), (255, 116, 0), (255, 104, 0), (255, 93, 0), (255, 81, 0), (255, 69, 0), (255, 58, 0), (255, 46, 0), (255, 34, 0), (255, 23, 0), (255, 11, 0),            # orange to red
                   (255, 0, 0)]                                                                                                                                                            # red

        terrain = [(0, 100, 0), (19, 107, 0), (38, 114, 0), (57, 121, 0), (76, 129, 0), (95, 136, 0), (114, 143, 0), (133, 150, 0), (152, 158, 0), (171, 165, 0), (190, 172, 0),                   # dark green to golden rod yellow
                   (210, 180, 0), (210, 167, 5), (210, 155, 10), (210, 142, 15), (210, 130, 20), (210, 117, 25),                                                                                   # golden rod yellow to orange brown
                   (210, 105, 30), (188, 94, 25), (166, 83, 21), (145, 72, 17), (123, 61, 13), (101, 50, 9),                                                                                       # orange brown to dark brown
                   (80, 40, 5), (95, 59, 27), (111, 79, 50), (127, 98, 73), (143, 118, 95), (159, 137, 118),(175, 157, 141), (191, 176, 164), (207, 196, 186), (223, 215, 209), (239, 235, 232),   # dark brown to white
                   (255, 255, 255)]                                                                                                                                                                # white

        aqua = [(150, 255, 255), (136, 240, 250), (122, 226, 245), (109, 212, 240), (95, 198, 235), (81, 184, 230), (68, 170, 225), (54, 156, 220), (40, 142, 215), (27, 128, 210), (13, 114, 205), # aqua to blue
                (0, 100, 200), (0, 94, 195), (0, 89, 191), (0, 83, 187), (0, 78, 182), (0, 72, 178), (0, 67, 174), (0, 61, 170), (0, 56, 165), (0, 50, 161), (0, 45, 157), (0, 40, 153),            # blue to navy blue
                (0, 36, 143), (0, 32, 134), (0, 29, 125), (0, 25, 115), (0, 21, 106), (0, 18, 97), (0, 14, 88), (0, 10, 78), (0, 7, 69), (0, 3, 60), (0, 0, 51)]                                    # navy blue to dark navy blue


        if (colorRampEnum == ColorRampEnum.COLOR_RAMP_HUE):
            return hue

        elif (colorRampEnum == ColorRampEnum.COLOR_RAMP_TERRAIN):
            return terrain

        elif (colorRampEnum == ColorRampEnum.COLOR_RAMP_AQUA):
            return aqua

    @classmethod
    def generateCustomColorRamp(cls, colors=[], interpolatedPoints=10):
        """
        Accepts a list of RGB tuples and interpolates between them to create a custom color ramp.
        Returns the color ramp as a list of RGB tuples.
        """
        if not (isinstance(colors, list)):
            print('COLOR RAMP GENERATOR WARNING: colors must be passed in as a list of RGB tuples.')
            raise

        numColors = len(colors)

        colorRamp = []

        # Iterate over colors
        for index in range (0, numColors - 1):
            bottomColor = colors[index]
            topColor = colors[index + 1]

            colorRamp.append(bottomColor)

            # Calculate slopes
            rSlope = (topColor[0] - bottomColor[0]) / float(interpolatedPoints)
            gSlope = (topColor[1] - bottomColor[1]) / float(interpolatedPoints)
            bSlope = (topColor[2] - bottomColor[2]) / float(interpolatedPoints)

            # Interpolate colors
            for point in range(1, interpolatedPoints):
                red = int(rSlope * point + bottomColor[0])
                green = int(gSlope * point + bottomColor[1])
                blue = int(bSlope * point + bottomColor[2])
                color = (red, green, blue)

                # Make sure the color ramp contains unique colors
                if not (color in colorRamp):
                    colorRamp.append(color)

        # Append the last color
        colorRamp.append(colors[-1])

        return colorRamp

    @classmethod
    def mapColorRampToValues(cls, colorRamp, minValue, maxValue, alpha=1.0):
        """
        Creates color ramp based on min and max values of all the raster pixels from all rasters. If pixel value is one
        of the no data values it will be excluded in the color ramp interpolation. Returns colorRamp, slope, intercept

        :param colorRamp: A list of RGB tuples representing a color ramp (e.g.: results of either generate color ramp method)
        :param minValue: Minimum value of range of values to map to color ramp
        :param maxValue: Maximum value of range of values to map to color ramp
        :param alpha: Decimal representing transparency (e.g.: 0.8)

        :rtype : MappedColorRamp
        """
        minRampIndex = 0  # Always zero
        maxRampIndex = float(len(colorRamp) - 1)  # Map color ramp indices to values using equation of a line

        # Resulting equation will be:
        # rampIndex = slope * value + intercept
        if minValue != maxValue:
            slope = (maxRampIndex - minRampIndex) / (maxValue - minValue)
            intercept = maxRampIndex - (slope * maxValue)
        else:
            slope = 0
            intercept = minRampIndex

        # Return color ramp, slope, and intercept to interpolate by value
        mappedColorRamp = MappedColorRamp(colorRamp=colorRamp,
                                          slope=slope,
                                          intercept=intercept,
                                          min=minValue,
                                          max=maxValue,
                                          alpha=alpha)

        return mappedColorRamp

    def isNumber(self, value):
        """
        Validate whether a value is a number or not
        """
        try:
            str(value)
            float(value)
            return True

        except ValueError:
            return False
