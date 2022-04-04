"""
This will allow you to choose which GPUs to use with Commandline Rendering.
Launch Blender with the script like this: 

$ blender -b -P enable_gpus.py blendfile.blend -a

"""
import bpy


def enable_gpus(device_type, use_cpus=False, filter_by_name=None):
    """
    Enable GPU rendering and configure GPUs.

    device_type: OPTIX or CUDA
    use_cpus: render with GPUs AND CPUS
    filter_by_name: Choose GPU(s) by name, e.g. "1080" or "3080"
    """

    preferences = bpy.context.preferences
    cycles_preferences = preferences.addons["cycles"].preferences
    devices = bpy.context.preferences.addons["cycles"].preferences.get_devices_for_type(device_type)

    # use GPU rendering
    bpy.context.scene.cycles.device = "GPU"
    # OPTIX or CUDA?
    cycles_preferences.compute_device_type = device_type

    for device in devices:
        # first activate all devices
        device.use = True
        # disable devices that don't match the filter_by_name
        if filter_by_name and filter_by_name not in device.name:
            device.use = False
        # disable CPU if necessary
        if device.type == "CPU":
            device.use = use_cpus

    # return activated devices for printing to check if everything worked
    activated_devices = [d.name for d in devices if d.use]

    return activated_devices


print(enable_gpus("OPTIX", filter_by_name="3080"))
