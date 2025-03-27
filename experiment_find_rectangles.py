import cv2
import numpy as np

def find_rectangles1(image):
    # Visualize original image
    cv2.imshow("Original Image", cv2.resize(image, None, fx=0.5, fy=0.5))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # This gets rid of the background gray lines.
    _, binary = cv2.threshold(gray, 230, 255, cv2.THRESH_TOZERO_INV)

    # # Visualize thresholded image
    cv2.imshow("Thresholded Image", cv2.resize(binary, None, fx=0.5, fy=0.5))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Find edges using Canny edge detection
    edges = cv2.Canny(binary, 50, 150)

    # Visualize edges
    cv2.imshow("Edges", cv2.resize(edges, None, fx=0.5, fy=0.5))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Find lines using probabilistic Hough Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=25, minLineLength=1, maxLineGap=15)

    # Create an empty mask to draw lines
    mask = np.zeros_like(gray)

    # Draw lines on the mask
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(mask, (x1, y1), (x2, y2), 255, 2)

    # Visualize Hough lines
    cv2.imshow("Hough Lines", cv2.resize(mask, None, fx=0.5, fy=0.5))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Apply morphological operations to enhance rectangles
    kernel = np.ones((5, 5), np.uint8)
    dilated_mask = cv2.dilate(mask, kernel, iterations=6)
    eroded_mask = cv2.erode(dilated_mask, kernel, iterations=5)

    # Visualize enhanced mask
    cv2.imshow("Enhanced Mask", cv2.resize(eroded_mask, None, fx=0.5, fy=0.5))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Find contours in the mask
    contours, _ = cv2.findContours(eroded_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)

    # Filter contours by shape
    rectangles = []
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) == 4:
            # Get the bounding box of the contour
            x, y, w, h = cv2.boundingRect(approx)
            rectangles.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "color": cv2.mean(image[y:y + h, x:x + w])
            })

    return rectangles

def find_rectangles2(image):
  """
  Finds rectangles in an image and returns their coordinates and color.

  Args:
    image: The image to be processed.

  Returns:
    A list of dictionaries, where each dictionary contains the following keys:
      - x: The x-coordinate of the top-left corner of the rectangle.
      - y: The y-coordinate of the top-left corner of the rectangle.
      - w: The width of the rectangle.
      - h: The height of the rectangle.
      - color: The color of the rectangle as a tuple of (B, G, R) values.
  """

  # Convert the image to grayscale
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

  # Find edges using Canny edge detection
  edges = cv2.Canny(gray, 50, 60)

  # Find contours in the image
  contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

  # Filter contours by shape
  rectangles = []
  for contour in contours:
    approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
    if len(approx) == 4:
      # Get the bounding box of the contour
      x, y, w, h = cv2.boundingRect(approx)
      rectangles.append({
          "x": x,
          "y": y,
          "w": w,
          "h": h,
          "color": cv2.mean(image[y:y+h, x:x+w])
      })

  return rectangles

find_rectangles = find_rectangles1

# Read the image
image = cv2.imread("docs/examples/images/email_subject.png")
rectangles = find_rectangles(image)

# Print the results
for rectangle in rectangles:
  print(f"Rectangle: x={rectangle['x']}, y={rectangle['y']}, w={rectangle['w']}, h={rectangle['h']}, color={rectangle['color']}")

# Draw the rectangles on the image
for rectangle in rectangles:
  cv2.rectangle(image, (rectangle['x'], rectangle['y']), (rectangle['x'] + rectangle['w'], rectangle['y'] + rectangle['h']), (0, 255, 0), 2)

# Display the image with rectangles
cv2.imshow("Image with Rectangles", cv2.resize(image, None , fx=0.5, fy=0.5))
cv2.waitKey(0)
cv2.destroyAllWindows()
