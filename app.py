import os
from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
from pillow_heif import register_heif_opener
import math

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/output'

# Ensure the upload and output folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Register HEIF opener
register_heif_opener()

def convert_heic_to_jpg(heic_path):
    image = Image.open(heic_path)
    jpg_path = os.path.splitext(heic_path)[0] + '.jpg'
    image.save(jpg_path, 'JPEG')
    return jpg_path

def create_collage(folder_path, output_path, base_image_size=(400, 400), scale_factor=2, frame_width=80):
    # Get all image files from the folder
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.heic')
    image_paths = set()  # Use a set to avoid duplicates
    for f in os.listdir(folder_path):
        if f.lower().endswith(image_extensions) and os.path.isfile(os.path.join(folder_path, f)) and f != 'flower.png':
            file_path = os.path.join(folder_path, f)
            base_name = os.path.splitext(f)[0]
            if f.lower().endswith('.heic'):
                file_path = convert_heic_to_jpg(file_path)
                # Remove the original HEIC file from consideration
                image_paths.discard(os.path.join(folder_path, base_name + '.heic'))
            image_paths.add(file_path)
    
    image_paths = sorted(list(image_paths))
    num_images = len(image_paths)

    # Calculate layout
    if num_images <= 4:
        cols, rows = 2, 2
    elif num_images <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 3, 3

    # Calculate scaled image size and collage size
    image_size = (base_image_size[0] * scale_factor, base_image_size[1] * scale_factor)
    collage_width = cols * image_size[0] + 2 * frame_width
    collage_height = rows * image_size[1] + 2 * frame_width

    # Create a new image for the collage with white background
    collage = Image.new('RGBA', (collage_width, collage_height), (255, 255, 255, 255))

    # Paste images into the collage
    for index, image_path in enumerate(image_paths):
        if index >= cols * rows:
            break  # Stop if we've filled all spots in the layout

        row = index // cols
        col = index % cols

        image = Image.open(image_path)
        image = image.resize(image_size, resample=Image.BICUBIC)
        image = image.convert('RGBA')

        x_offset = col * image_size[0] + frame_width
        y_offset = row * image_size[1] + frame_width

        collage.paste(image, (x_offset, y_offset), image)

    # Add flower frame
    flower = Image.open('flower.png')  # Make sure you have this file in the same directory
    flower = flower.resize((frame_width * 2, frame_width * 2))

    # Top and bottom edges
    for x in range(0, collage_width, frame_width * 2):
        collage.paste(flower, (x, 0), flower)
        collage.paste(flower, (x, collage_height - frame_width * 2), flower)

    # Left and right edges
    for y in range(0, collage_height, frame_width * 2):
        collage.paste(flower, (0, y), flower)
        collage.paste(flower, (collage_width - frame_width * 2, y), flower)

    # Save the collage
    collage.save(output_path)
    return f"Collage created with {min(num_images, cols * rows)} images. Layout: {cols}x{rows}. Collage size: {collage.size}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_files = request.files.getlist("files[]")
        for file in uploaded_files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('manage_images'))
    return render_template('index.html')

@app.route('/manage_images', methods=['GET', 'POST'])
def manage_images():
    if request.method == 'POST':
        if 'delete' in request.form:
            filename = request.form['delete']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        elif 'create_collage' in request.form:
            scale_factor = int(request.form.get('scale_factor', 2))
            frame_width = int(request.form.get('frame_width', 80))
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], 'collage.png')
            create_collage(app.config['UPLOAD_FOLDER'], output_path, scale_factor=scale_factor, frame_width=frame_width)
            return send_file(output_path, as_attachment=True)

    images = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    return render_template('manage_images.html', images=images)

if __name__ == '__main__':
    app.run(debug=True)