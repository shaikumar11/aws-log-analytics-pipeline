"""
Diagnostic: builds the same zip deploy_lambda.py would upload, but locally,
and prints exactly what's inside it so we can catch packaging issues.
"""

import io
import zipfile

with io.BytesIO() as buf:
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write("handler.py")
    buf.seek(0)
    zip_bytes = buf.read()

print(f"Zip size: {len(zip_bytes)} bytes\n")

with io.BytesIO(zip_bytes) as buf:
    with zipfile.ZipFile(buf) as z:
        print("Contents of zip:")
        for info in z.infolist():
            print(f"  {info.filename}  ({info.file_size} bytes)")

        print("\n--- handler.py content as seen inside the zip ---\n")
        content = z.read("handler.py").decode("utf-8")
        print(content)