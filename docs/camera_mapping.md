# Camera Mapping

Current camera mapping after the latest USB reconnection:

| Camera index | Position | Status |
|--------------|----------|--------|
| 0 | Right arm camera | Active |
| 1 | Left arm camera | Active |
| 2 | Head camera | Active; PetPal default main camera |
| 3 | Laptop / non-main camera | Active |

Survey images are saved under:

```text
outputs/camera_survey/
```

Latest survey contact sheet:

```text
outputs/camera_survey/20260713_232820/camera_contact_sheet.jpg
```

If USB devices are reconnected, run another camera survey before changing PetPal behavior that depends on camera
position.
