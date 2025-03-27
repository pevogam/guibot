import cv2
import numpy as np

def find_rectangles1(image):
    """Detect quadrilateral contours reconstructed from Hough line segments.

    This original, interactive experiment converts the image to grayscale,
    extracts Canny edges, and uses ``HoughLinesP`` to draw detected segments
    into a mask.  Dilation followed by erosion joins nearby or interrupted
    segments; tree contours from that mask are polygonally approximated, and
    every four-corner approximation is returned as its axis-aligned bounding
    box.  Intermediate images are displayed to explain each processing stage.

    This is a standalone baseline: it does not call another ``find_rectangles``
    method or filter candidates by size, rectangularity, or side coverage.
    Consequently it is sensitive to the Hough and morphology settings and can
    merge neighboring controls or accept quadrilaterals with weak borders.
    """
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
  Detect four-corner shapes directly from external Canny contours.

  The image is converted to grayscale and passed through Canny; only external
  contours are retrieved.  Each contour is simplified with ``approxPolyDP``,
  and a contour with exactly four vertices is represented by its axis-aligned
  bounding box.  This removes the Hough transform, morphology, and diagnostic
  windows used by :func:`find_rectangles1`, making it the simplest baseline.

  The method is standalone and intentionally has no size, side-support, or
  duplicate filtering.  It therefore finds clear isolated outlines cheaply,
  but shared borders and broken or nested UI rectangles are commonly missed.
  Every result contains ``x``, ``y``, ``w``, ``h``, and the mean BGR ``color``.
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


def rectangle_side_support(horizontal, vertical, x, y, w, h, tolerance=3):
    """Return the detected-line coverage for each side of a rectangle.

    The horizontal and vertical masks may place a detected line a few pixels
    away from the contour's bounding box.  Search a narrow band around every
    expected side and retain the best-covered row or column.

    Returns the support for the top, bottom, left, and right sides as values
    between zero and one.
    """
    if horizontal.shape != vertical.shape:
        raise ValueError("Horizontal and vertical masks must have equal shapes")
    if w <= 0 or h <= 0:
        return 0.0, 0.0, 0.0, 0.0

    image_height, image_width = horizontal.shape[:2]
    x_start, x_end = max(x, 0), min(x + w, image_width)
    y_start, y_end = max(y, 0), min(y + h, image_height)
    horizontal_span = x_end - x_start
    vertical_span = y_end - y_start
    if horizontal_span <= 0 or vertical_span <= 0:
        return 0.0, 0.0, 0.0, 0.0

    def horizontal_support(expected_y):
        first_row = max(expected_y - tolerance, 0)
        last_row = min(expected_y + tolerance + 1, image_height)
        return max(
            (
                np.count_nonzero(horizontal[row, x_start:x_end])
                / horizontal_span
                for row in range(first_row, last_row)
            ),
            default=0.0,
        )

    def vertical_support(expected_x):
        first_column = max(expected_x - tolerance, 0)
        last_column = min(expected_x + tolerance + 1, image_width)
        return max(
            (
                np.count_nonzero(vertical[y_start:y_end, column])
                / vertical_span
                for column in range(first_column, last_column)
            ),
            default=0.0,
        )

    return (
        horizontal_support(y),
        horizontal_support(y + h - 1),
        vertical_support(x),
        vertical_support(x + w - 1),
    )


def remove_duplicate_rectangles(
    rectangles, iou_threshold=0.85, edge_tolerance=3
):
    """Remove repeated inner/outer contours representing the same rectangle.

    Larger candidates win.  Two candidates are considered duplicates when
    their intersection-over-union is high, or when all corresponding edges
    differ by no more than ``edge_tolerance`` pixels.
    """
    candidates = sorted(
        set(rectangles),
        key=lambda rectangle: (
            -(rectangle[2] * rectangle[3]),
            rectangle[1],
            rectangle[0],
            rectangle[2],
            rectangle[3],
        ),
    )
    unique = []

    for candidate in candidates:
        x1, y1, w1, h1 = candidate
        candidate_right = x1 + w1
        candidate_bottom = y1 + h1
        candidate_area = w1 * h1
        duplicate = False

        for accepted in unique:
            x2, y2, w2, h2 = accepted
            accepted_right = x2 + w2
            accepted_bottom = y2 + h2

            matching_edges = (
                abs(x1 - x2) <= edge_tolerance
                and abs(y1 - y2) <= edge_tolerance
                and abs(candidate_right - accepted_right) <= edge_tolerance
                and abs(candidate_bottom - accepted_bottom) <= edge_tolerance
            )

            intersection_width = max(
                0, min(candidate_right, accepted_right) - max(x1, x2)
            )
            intersection_height = max(
                0, min(candidate_bottom, accepted_bottom) - max(y1, y2)
            )
            intersection = intersection_width * intersection_height
            union = candidate_area + w2 * h2 - intersection
            iou = intersection / union if union else 0.0

            if matching_edges or iou >= iou_threshold:
                duplicate = True
                break

        if not duplicate:
            unique.append(candidate)

    return sorted(unique, key=lambda rectangle: (rectangle[1], rectangle[0]))


def find_rectangles3(image):
    """Detect closed rectangles from separate horizontal and vertical masks.

    After grayscale conversion and light Gaussian blur, Canny edges are closed
    across short gaps.  Directional morphology then retains long horizontal
    and vertical strokes in separate masks.  Tree contours of their union
    provide bounding-box proposals, which must meet minimum dimensions and
    have at least 45 percent line coverage on all four sides as measured by
    :func:`rectangle_side_support` within a small positional tolerance.

    This method does not call versions 1 or 2.  It uses
    :func:`remove_duplicate_rectangles` to collapse inner/outer edge contours.
    It is more selective than the baselines, but a shared border can connect
    adjacent controls into one contour and incomplete borders remain difficult.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 30, 100)

    height, width = gray.shape

    horizontal_length = max(15, width // 60)
    vertical_length = max(12, height // 60)
    gap = 7

    horizontal = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (gap, 1)),
    )
    horizontal = cv2.morphologyEx(
        horizontal,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (horizontal_length, 1)
        ),
    )

    vertical = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, gap)),
    )
    vertical = cv2.morphologyEx(
        vertical,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, vertical_length)
        ),
    )

    line_mask = cv2.bitwise_or(horizontal, vertical)
    contours, _ = cv2.findContours(
        line_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    rectangles = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if w < 20 or h < 14 or w * h < 400:
            continue

        support = rectangle_side_support(
            horizontal, vertical, x, y, w, h
        )
        if min(support) < 0.45:
            continue

        rectangles.append((x, y, w, h))

    rectangles = remove_duplicate_rectangles(rectangles)
    return [
        {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "color": cv2.mean(image[y:y + h, x:x + w]),
        }
        for x, y, w, h in rectangles
    ]


def merge_collinear_segments(segments, axis_tolerance=2, gap_tolerance=5):
    """Merge overlapping line segments lying on approximately the same axis."""
    groups = []
    for axis, start, end in sorted(segments):
        candidates = []
        for index, group in enumerate(groups):
            if abs(axis - group["axis"]) > axis_tolerance:
                continue
            if start > group["end"] + gap_tolerance:
                continue
            if end < group["start"] - gap_tolerance:
                continue

            overlap = max(
                0, min(end, group["end"]) - max(start, group["start"]) + 1
            )
            candidates.append(
                (overlap, -abs(axis - group["axis"]), index)
            )

        if not candidates:
            groups.append(
                {
                    "axes": [axis],
                    "axis": axis,
                    "start": start,
                    "end": end,
                }
            )
            continue

        group = groups[max(candidates)[2]]
        group["axes"].append(axis)
        group["axis"] = int(round(np.median(group["axes"])))
        group["start"] = min(group["start"], start)
        group["end"] = max(group["end"], end)

    return [
        (group["axis"], group["start"], group["end"])
        for group in groups
    ]


def find_rectangles4(image):
    """Find atomic bordered cells by pairing axis-aligned line segments.

    OpenCV's line-segment detector supplies candidate strokes.  Nearly
    horizontal and vertical strokes are classified, then consolidated by
    :func:`merge_collinear_segments`.  Pairs of horizontal strokes are examined
    for adjacent supporting vertical strokes; pairing only adjacent verticals
    and rejecting a full internal horizontal divider favors individual table
    cells over unions of neighboring cells.  The four sides are finally checked
    with :func:`rectangle_side_support`.

    Unlike :func:`find_rectangles3`, a rectangle need not exist as an isolated
    contour, so neighboring controls may share an edge.  Method 3 is still
    called for closed contours it handles better; both proposal sets are joined
    with :func:`remove_duplicate_rectangles`.  The result improves bordered
    grids but cannot recover regions expressed only by a background-color
    change.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    height, width = gray.shape

    horizontal_minimum = max(15, width // 100)
    vertical_minimum = max(12, height // 100)
    maximum_slope = 0.04

    detector = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    detected = detector.detect(gray)[0]
    horizontal_segments = []
    vertical_segments = []

    if detected is not None:
        for x1, y1, x2, y2 in detected[:, 0]:
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            if (
                dx >= horizontal_minimum
                and dy <= max(1.5, maximum_slope * dx)
            ):
                horizontal_segments.append(
                    (
                        int(round((y1 + y2) / 2)),
                        int(round(min(x1, x2))),
                        int(round(max(x1, x2))),
                    )
                )
            elif (
                dy >= vertical_minimum
                and dx <= max(1.5, maximum_slope * dy)
            ):
                vertical_segments.append(
                    (
                        int(round((x1 + x2) / 2)),
                        int(round(min(y1, y2))),
                        int(round(max(y1, y2))),
                    )
                )

    horizontal_segments = merge_collinear_segments(horizontal_segments)
    vertical_segments = merge_collinear_segments(vertical_segments)

    horizontal_mask = np.zeros_like(gray)
    vertical_mask = np.zeros_like(gray)
    for y, x1, x2 in horizontal_segments:
        cv2.line(horizontal_mask, (x1, y), (x2, y), 255, 1)
    for x, y1, y2 in vertical_segments:
        cv2.line(vertical_mask, (x, y1), (x, y2), 255, 1)

    corner_tolerance = 4
    paired_rectangles = []
    horizontal_segments = sorted(horizontal_segments)
    vertical_segments = sorted(vertical_segments)

    for index, top in enumerate(horizontal_segments):
        top_y, top_x1, top_x2 = top
        for bottom_y, bottom_x1, bottom_x2 in horizontal_segments[index + 1:]:
            rectangle_height = bottom_y - top_y + 1
            if rectangle_height < 14:
                continue

            overlap_left = max(top_x1, bottom_x1)
            overlap_right = min(top_x2, bottom_x2)
            if overlap_right - overlap_left + 1 < 20:
                continue

            supporting_verticals = sorted(
                segment
                for segment in vertical_segments
                if overlap_left - corner_tolerance
                <= segment[0]
                <= overlap_right + corner_tolerance
                and segment[1] <= top_y + corner_tolerance
                and segment[2] >= bottom_y - corner_tolerance
            )

            # Adjacent supporting lines describe atomic cells.  Pairing every
            # possible combination would produce all unions of a table's cells.
            for left, right in zip(
                supporting_verticals, supporting_verticals[1:]
            ):
                left_x = left[0]
                right_x = right[0]
                rectangle_width = right_x - left_x + 1
                if rectangle_width < 20 or rectangle_width * rectangle_height < 400:
                    continue

                top_covers_corners = (
                    top_x1 - corner_tolerance <= left_x
                    and top_x2 + corner_tolerance >= right_x
                )
                bottom_covers_corners = (
                    bottom_x1 - corner_tolerance <= left_x
                    and bottom_x2 + corner_tolerance >= right_x
                )
                if not top_covers_corners or not bottom_covers_corners:
                    continue

                has_horizontal_divider = any(
                    top_y + corner_tolerance < segment[0]
                    < bottom_y - corner_tolerance
                    and segment[1] <= left_x + corner_tolerance
                    and segment[2] >= right_x - corner_tolerance
                    for segment in horizontal_segments
                )
                if has_horizontal_divider:
                    continue

                support = rectangle_side_support(
                    horizontal_mask,
                    vertical_mask,
                    left_x,
                    top_y,
                    rectangle_width,
                    rectangle_height,
                )
                if min(support) < 0.45:
                    continue

                paired_rectangles.append(
                    (left_x, top_y, rectangle_width, rectangle_height)
                )

    # Keep the contour-based proposals too: line pairing recovers shared and
    # open contours, while method 3 remains better at some large containers.
    contour_rectangles = [
        (rectangle["x"], rectangle["y"], rectangle["w"], rectangle["h"])
        for rectangle in find_rectangles3(image)
    ]
    rectangles = remove_duplicate_rectangles(
        contour_rectangles + paired_rectangles
    )
    return [
        {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "color": cv2.mean(image[y:y + h, x:x + w]),
        }
        for x, y, w, h in rectangles
    ]


def find_rectangles_by_color(
    image, color_step=8, minimum_fill=0.60, minimum_area=400
):
    """Find rectangular connected regions with approximately uniform colors."""
    if color_step <= 0 or color_step > 255:
        raise ValueError("The color quantization step must be between 1 and 255")

    height, width = image.shape[:2]
    color_levels = 255 // color_step + 1
    quantized = image.astype(np.uint16) // color_step
    color_codes = (
        quantized[:, :, 0].astype(np.uint32)
        + color_levels * quantized[:, :, 1].astype(np.uint32)
        + color_levels * color_levels * quantized[:, :, 2].astype(np.uint32)
    )
    colors, color_counts = np.unique(color_codes, return_counts=True)

    rectangles = []
    for color, color_count in zip(colors, color_counts):
        if color_count < minimum_area:
            continue

        color_mask = np.uint8(color_codes == color) * 255
        component_count, _, component_stats, _ = (
            cv2.connectedComponentsWithStats(color_mask, connectivity=8)
        )
        for component in range(1, component_count):
            x, y, w, h, area = component_stats[component]
            x, y, w, h, area = map(int, (x, y, w, h, area))
            bounding_area = w * h

            if w < 20 or h < 14 or bounding_area < minimum_area:
                continue
            if bounding_area > 0.98 * width * height:
                continue
            if area / bounding_area < minimum_fill:
                continue

            rectangles.append((x, y, w, h))

    return rectangles


def find_rectangles5(image):
    """Combine line/contour geometry with approximately uniform color regions.

    :func:`find_rectangles4` supplies bordered rectangles (and, transitively,
    the closed-contour candidates from method 3).  In parallel,
    :func:`find_rectangles_by_color` quantizes BGR colors, finds connected
    components, and retains sufficiently large components that fill most of
    their bounding boxes.  :func:`remove_duplicate_rectangles` then removes
    only near-identical geometry before mean region colors are calculated.

    The color path detects borderless panels and controls that methods 3 and 4
    miss.  Because containment alone is not treated as duplication, this method
    deliberately preserves both small regions and some enclosing parents; that
    makes it a broad proposal generator as well as a usable detector.
    """
    geometry_rectangles = [
        (rectangle["x"], rectangle["y"], rectangle["w"], rectangle["h"])
        for rectangle in find_rectangles4(image)
    ]
    color_rectangles = find_rectangles_by_color(image)
    rectangles = remove_duplicate_rectangles(
        geometry_rectangles + color_rectangles,
        iou_threshold=0.80,
        edge_tolerance=4,
    )
    return [
        {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "color": cv2.mean(image[y:y + h, x:x + w]),
        }
        for x, y, w, h in rectangles
    ]


def _separator_groups(scores, threshold, minimum, maximum):
    """Group neighboring separator pixels into single boundary candidates."""
    positions = np.flatnonzero(scores >= threshold) + 1
    positions = positions[
        (positions >= minimum) & (positions <= maximum)
    ]
    if positions.size == 0:
        return []

    group_starts = np.flatnonzero(np.diff(positions) > 2) + 1
    return np.split(positions, group_starts)


def partition_atomic_regions(
    image,
    proposals,
    color_difference=10,
    gradient_support=0.70,
    proposal_support=0.55,
    minimum_width=20,
    minimum_height=14,
    maximum_depth=16,
):
    """Recursively partition an image into small, non-overlapping regions.

    A split can be introduced by a color transition spanning most of the
    current region, or by an edge of an existing rectangle proposal spanning
    most of it.  Recursing after every split is important for UI layouts: a
    divider which covers only one row or column of controls becomes a strong
    separator once its enclosing region has been isolated.
    """
    height, width = image.shape[:2]
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.int16)
    leaves = []

    def add_gradient_candidates(region, candidates):
        region_height, region_width = region.shape[:2]

        if region_width >= 2 * minimum_width:
            differences = np.max(
                np.abs(np.diff(region, axis=1)), axis=2
            )
            support = np.mean(
                differences >= color_difference, axis=0
            )
            strength = np.mean(differences, axis=0)
            groups = _separator_groups(
                support,
                gradient_support,
                minimum_width,
                region_width - minimum_width,
            )
            for group in groups:
                position = int(
                    group[np.argmax(support[group - 1])]
                )
                candidates.append(
                    (
                        float(support[position - 1]),
                        float(strength[position - 1]),
                        "vertical",
                        position,
                    )
                )

        if region_height >= 2 * minimum_height:
            differences = np.max(
                np.abs(np.diff(region, axis=0)), axis=2
            )
            support = np.mean(
                differences >= color_difference, axis=1
            )
            strength = np.mean(differences, axis=1)
            groups = _separator_groups(
                support,
                gradient_support,
                minimum_height,
                region_height - minimum_height,
            )
            for group in groups:
                position = int(
                    group[np.argmax(support[group - 1])]
                )
                candidates.append(
                    (
                        float(support[position - 1]),
                        float(strength[position - 1]),
                        "horizontal",
                        position,
                    )
                )

    def add_proposal_candidates(x, y, w, h, candidates):
        for proposal_x, proposal_y, proposal_w, proposal_h in proposals:
            overlap_x = max(
                0,
                min(x + w, proposal_x + proposal_w)
                - max(x, proposal_x),
            )
            overlap_y = max(
                0,
                min(y + h, proposal_y + proposal_h)
                - max(y, proposal_y),
            )

            vertical_support = overlap_y / h
            if vertical_support >= proposal_support:
                for edge in (proposal_x, proposal_x + proposal_w):
                    position = edge - x
                    if minimum_width <= position <= w - minimum_width:
                        candidates.append(
                            (
                                vertical_support,
                                0.0,
                                "vertical",
                                position,
                            )
                        )

            horizontal_support = overlap_x / w
            if horizontal_support >= proposal_support:
                for edge in (proposal_y, proposal_y + proposal_h):
                    position = edge - y
                    if minimum_height <= position <= h - minimum_height:
                        candidates.append(
                            (
                                horizontal_support,
                                0.0,
                                "horizontal",
                                position,
                            )
                        )

    def subdivide(x, y, w, h, depth):
        if depth >= maximum_depth:
            leaves.append((x, y, w, h))
            return

        candidates = []
        add_gradient_candidates(lab[y:y + h, x:x + w], candidates)
        add_proposal_candidates(x, y, w, h, candidates)
        if not candidates:
            leaves.append((x, y, w, h))
            return

        _, _, axis, position = max(
            candidates, key=lambda candidate: candidate[:2]
        )
        if axis == "vertical":
            subdivide(x, y, position, h, depth + 1)
            subdivide(
                x + position, y, w - position, h, depth + 1
            )
        else:
            subdivide(x, y, w, position, depth + 1)
            subdivide(
                x, y + position, w, h - position, depth + 1
            )

    subdivide(0, 0, width, height, 0)
    return leaves


def find_crossing_color_overlays(
    image, leaves, maximum_area_fraction=0.25
):
    """Return small color regions which cross the leaf partition.

    A recursive axis-aligned partition cannot represent an overlay without
    also cutting the content behind it.  Keep small color proposals that cross
    leaf boundaries so dialogs and floating panels can overlap the base
    layout.  Large proposals are deliberately rejected because they are more
    likely to be enclosing parent regions than useful OCR regions.
    """
    image_area = image.shape[0] * image.shape[1]
    overlays = []

    def contains(outer, inner):
        outer_x, outer_y, outer_w, outer_h = outer
        inner_x, inner_y, inner_w, inner_h = inner
        return (
            outer_x <= inner_x
            and outer_y <= inner_y
            and outer_x + outer_w >= inner_x + inner_w
            and outer_y + outer_h >= inner_y + inner_h
        )

    for proposal in find_rectangles_by_color(image):
        proposal_x, proposal_y, proposal_w, proposal_h = proposal
        if proposal_w * proposal_h > maximum_area_fraction * image_area:
            continue

        for leaf in leaves:
            leaf_x, leaf_y, leaf_w, leaf_h = leaf
            intersection_width = max(
                0,
                min(proposal_x + proposal_w, leaf_x + leaf_w)
                - max(proposal_x, leaf_x),
            )
            intersection_height = max(
                0,
                min(proposal_y + proposal_h, leaf_y + leaf_h)
                - max(proposal_y, leaf_y),
            )
            if intersection_width == 0 or intersection_height == 0:
                continue

            if not contains(proposal, leaf) and not contains(leaf, proposal):
                overlays.append(proposal)
                break

    return overlays


def find_rectangles6(image):
    """Partition the screen into atomic UI regions and retain small overlays.

    :func:`find_rectangles5` first provides a deliberately broad mixture of
    line-, contour-, and color-based proposals.  Their edges, together with
    strong Lab color transitions spanning most of the current region, guide
    :func:`partition_atomic_regions`.  That function recursively subdivides the
    image, allowing a short local divider to become useful after its containing
    row or column is isolated.  The resulting leaves cover the complete image
    without gaps or overlaps and omit their larger enclosing parent regions.

    A binary axis-aligned partition cannot represent a dialog floating across
    an underlying layout boundary.  :func:`find_crossing_color_overlays`
    therefore restores color proposals that cross leaf boundaries, while its
    maximum-area limit rejects likely parent containers.  A final call to
    :func:`remove_duplicate_rectangles` removes equivalent leaf/overlay boxes.
    This active experiment consequently favors numerous small, locally
    monotone OCR inputs while still representing dialogs and floating panels.
    """
    proposals = [
        (rectangle["x"], rectangle["y"], rectangle["w"], rectangle["h"])
        for rectangle in find_rectangles5(image)
    ]
    leaves = partition_atomic_regions(image, proposals)
    overlays = find_crossing_color_overlays(image, leaves)
    rectangles = remove_duplicate_rectangles(
        leaves + overlays,
        iou_threshold=0.80,
        edge_tolerance=4,
    )
    return [
        {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "color": cv2.mean(image[y:y + h, x:x + w]),
        }
        for x, y, w, h in rectangles
    ]


find_rectangles = find_rectangles6

if __name__ == "__main__":
    # Read the image
    image = cv2.imread("docs/examples/images/email_subject.png")
    rectangles = find_rectangles(image)

    # Print the results
    for rectangle in rectangles:
        print(
            f"Rectangle: x={rectangle['x']}, y={rectangle['y']}, "
            f"w={rectangle['w']}, h={rectangle['h']}, "
            f"color={rectangle['color']}"
        )

    # Draw the rectangles on the image
    for rectangle in rectangles:
        cv2.rectangle(
            image,
            (rectangle["x"], rectangle["y"]),
            (
                rectangle["x"] + rectangle["w"],
                rectangle["y"] + rectangle["h"],
            ),
            (0, 255, 0),
            2,
        )

    # Display the image with rectangles
    window_name = "Image with Rectangles"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, image.shape[1], image.shape[0])
    cv2.imshow(window_name, image)
    # Make sure to press ESC instead of closing the window.
    while True:
        key = cv2.waitKey(50)
        if key != -1 and (key & 0xFF) == 27:
            break
        try:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            # Some backends raise once the window has already been destroyed.
            break
    cv2.destroyAllWindows()
