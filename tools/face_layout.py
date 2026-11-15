"""One fixed transform per face, shared by its static pose and every animation frame."""
from PIL import Image

def layout(reference):
    box = reference.getbbox()
    if box is None: raise ValueError("Empty face")
    x0,y0,x1,y1 = box
    scale = min(1.65, 104/(x1-x0), 50/(y1-y0))
    if scale < 1.08: return 1.0, 0.0, 0.0
    return scale, 64-scale*(x0+x1)/2, 32-scale*(y0+y1)/2

def apply_layout(frame, transform):
    scale,tx,ty = transform
    if scale == 1: return frame.copy()
    # Resample once with the same mapping for the whole cycle, including closed eyes.
    return frame.transform((128,64), Image.Transform.AFFINE,
        (1/scale,0,-tx/scale,0,1/scale,-ty/scale),
        resample=Image.Resampling.NEAREST,fillcolor=0)
