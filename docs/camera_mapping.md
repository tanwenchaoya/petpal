# Camera Mapping

Current camera mapping after the latest USB reconnection:

| Camera index | Position | Status |
|--------------|----------|--------|
| 0 | Head camera | Active; PetPal default main camera |
| 1 | Right arm camera | Active |
| 2 | Left arm camera | Expected, but currently not enumerated |
| 3 | Laptop camera | Active |

Survey images are saved under:

```text
outputs/camera_survey/
```

If USB devices are reconnected, run another camera survey before changing PetPal behavior that depends on camera
position.
