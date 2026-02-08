import shutil
import subprocess
import sys
from PIL import Image
from io import BytesIO

class TerminalViewer:
    def is_sixel_supported(self):
        # Difficult to detect reliably without querying terminal which is async/complex.
        # We'll assume yes if the user asked for it or just check if img2sixel exists.
        return shutil.which("img2sixel") is not None

    def display(self, image_path):
        """
        Displays the image using img2sixel.
        """
        if not self.is_sixel_supported():
            print(f"[Image: {image_path}] (img2sixel not found)")
            return

        try:
            # Load image with PIL to handle various formats and potentially resize
            with Image.open(image_path) as img:
                # Resize if too huge to fit in terminal? 
                # img2sixel usually handles scaling, but we can ensure it's not massive.
                # Let's let img2sixel handle it with -w auto or similar if we wanted, 
                # but piping raw pixels allows us to control it.
                
                # Convert to RGB to ensure PPM compatibility
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize to reasonable width (e.g. 800px) to prevent massive spew
                max_width = 1000
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                # Save to PPM (portable pixmap) which img2sixel reads reliably from stdin
                # even if it lacks other library support.
                buf = BytesIO()
                img.save(buf, format='PPM')
                buf.seek(0)

                # Run img2sixel
                # -w auto: auto width? No, we resized already.
                subprocess.run(["img2sixel"], input=buf.read(), check=False)
                
        except Exception as e:
            print(f"Error displaying image: {e}")
