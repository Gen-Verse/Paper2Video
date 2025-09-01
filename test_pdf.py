import fitz  # PyMuPDF
import io
from PIL import Image
import os

def extract_and_combine_images(pdf_path, page_num, output_folder, image_index=0):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)

    # Extract images from the page
    page_images = page.get_images(full=True)

    image_list = []

    for img_index, img in enumerate(page_images):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        img_ext = base_image["ext"]

        # Get the image width and height
        img_width = base_image["width"]
        img_height = base_image["height"]

        # Get the image position on the page
        img_rect = img[1]  # This should be a tuple of (x0, y0, x1, y1) for image position
        print(f"img_rect: {img_rect}")  # Inspect img_rect

        # Check if img_rect is a tuple and unpack it
        if isinstance(img_rect, tuple) and len(img_rect) == 4:
            x0, y0, x1, y1 = img_rect
        else:
            print(f"Unexpected img_rect format: {img_rect}")
            continue  # Skip this image if the format is incorrect

        # Open the image data with PIL
        image = Image.open(io.BytesIO(image_bytes))

        # Store image data and its position
        image_list.append((image, x0, y0, img_width, img_height))

        print(f"✅ extract {image_index}: {img_ext} at position ({x0}, {y0})")
        image_index += 1

    # Now stitch the images together to create a large image
    if image_list:
        # Determine the size of the final image (max x and y positions + image dimensions)
        max_x = max([x0 + img_width for _, x0, _, img_width, _ in image_list])
        max_y = max([y0 + img_height for _, _, y0, _, img_height in image_list])

        # Create a blank canvas for the final large image
        large_image = Image.new("RGB", (max_x, max_y))

        # Paste each image onto the canvas at the correct position
        for image, x0, y0, _, _ in image_list:
            large_image.paste(image, (x0, y0))

        # Save the combined image
        combined_image_path = os.path.join(output_folder, f"combined_figure.png")
        large_image.save(combined_image_path)
        print(f"✅ image is saved at：{combined_image_path}")


# Example usage
# pdf_path = "C:\\Users\\87719\\Desktop\\AgenticIR-main\\dataset\\ControlNet.pdf"  # Replace with your PDF file path
# page_num = 0  # Replace with the page number where the images are located
# output_folder = "output_1"  # Replace with the output folder

# extract_and_combine_images(pdf_path, page_num, output_folder)
