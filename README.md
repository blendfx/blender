# Blender Scripts
In this repository we upload various scripts to improve our inhouse workflow with Blender.

## VRAIS Tools
The VRAIS tools are meant to help users of our free VR viewer VRAIS setup their VR scenes and upload the finished rendering to [vrais.io.](http://www.vrais.io)
### Installation
To install the vrais tools, simply download the script to your computer and install it as a Blender Addon from your User Preferences. 
In order to be able to upload to vrais.io you first need to copy the user token from your Account Settings on vrais.io. Then open up the preferences of the addon and paste the user token there.
The VRAIS Tools will appear in the Render section of the Properties editor in Blender.
### Usage
This addon assumes that you use it from within your active scene. For instance: You finish a rendering in Scene_01, you press the cubemap or upload button in Scene_01. The renderpath and camera stereo convergence from Scene_01 will be used by the addon.
### Creating a cubemap
Cubemaps have the advantage of making better use of the pixels in your VR rendering. If you render an equirectangular panorama the upper and lower thirds of the image will be
unnecessarily oversampled, hence wasting precious render time. A cubemap avoids that.
In order to render a cubemap you need to enable the Cube Map addon by Dalai Felinto. You find it in the Testing section of the Blender Addons.
That addon will render 12 images, left and right eye for each of the 6 sides of a cubemap. To upload that to vrais.io you need to stitch
these images to one long cubemap stripe. The "create cubemap" button will do that for you. 
### Upload to vrais.io
Once you have configured the addon by entering the user token in the User Prefs, you can upload your finished rendering to vrais.io by clicking on the upload button.
Before you do that make sure that you give your Rendering a title and a description. The stereo convergence will be automatically copied from your scene camera and transferred to vrais.io.

