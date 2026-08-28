import os
import sys
import subprocess
import numpy as np
import open3d as o3d

os.environ["GLFW_PLATFORM"] = "x11"

def ensure_package(package_name):
    """Installiert ein fehlendes Paket automatisch in der laufenden Python-Umgebung."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"\n[Auto-Setup] Paket '{package_name}' fehlt in dieser Umgebung. Installiere automatisch...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"[Auto-Setup] '{package_name}' wurde erfolgreich installiert!\n")
        except Exception as e:
            print(f"[FEHLER] Automatische Installation von '{package_name}' fehlgeschlagen: {e}")
            sys.exit()

def load_point_cloud_flexible(file_path):
    """Lädt Punktwolken (.ply, .pcd, .pts, .xyz, .e57) und aggregiert alle E57-Teilscans."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.e57':
        ensure_package("pye57")
        import pye57

        try:
            e57 = pye57.E57(file_path)
            all_coords = []
            all_colors = []

            for i in range(e57.scan_count):
                data = e57.read_scan_raw(i)
                
                if "cartesianX" in data:
                    x = data["cartesianX"]
                    y = data["cartesianY"]
                    z = data["cartesianZ"]

                    valid_mask = ~np.isnan(x) & ~np.isnan(y) & ~np.isnan(z)
                    
                    coords = np.column_stack((x[valid_mask], y[valid_mask], z[valid_mask]))
                    if len(coords) > 0:
                        all_coords.append(coords)

                    if "colorRed" in data and "colorGreen" in data and "colorBlue" in data:
                        r = data["colorRed"][valid_mask]
                        g = data["colorGreen"][valid_mask]
                        b = data["colorBlue"][valid_mask]
                        colors = np.column_stack((r, g, b))
                        
                        c_max = colors.max() if len(colors) > 0 else 1.0
                        if c_max > 255:
                            colors = colors / 65535.0
                        elif c_max > 1.0:
                            colors = colors / 255.0
                        
                        all_colors.append(colors)

            if not all_coords:
                print(f"\n[FEHLER] Keine gültigen Punkte in .e57 gefunden!")
                sys.exit()

            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(np.vstack(all_coords))
            
            if all_colors:
                pcd.colors = o3d.utility.Vector3dVector(np.vstack(all_colors))

        except Exception as e:
            print(f"\n[FEHLER] Die .e57-Datei konnte nicht verarbeitet werden: {e}")
            input("\nDrücke Enter zum Beenden...")
            sys.exit()
    else:
        pcd = o3d.io.read_point_cloud(file_path)

    if pcd.is_empty() or len(pcd.points) == 0:
        print(f"\n[FEHLER] Die Datei '{os.path.basename(file_path)}' enthält keine gültigen Punkte!")
        input("\nDrücke Enter zum Beenden...")
        sys.exit()

    return pcd

def check_and_scale_extent(pcds, label_name="Punktwolke"):
    """Prüft die Dimensionen der Punktwolke(n) und bietet Skalierung bei < 1 m an."""
    if not pcds:
        return pcds

    ref_pcd = pcds[0] if isinstance(pcds, list) else pcds
    min_b = ref_pcd.get_min_bound()
    max_b = ref_pcd.get_max_bound()
    extent = max_b - min_b
    max_dim = np.max(extent)

    print(f"\n -> Gemessene Ausdehnung ({label_name}):")
    print(f"    X = {extent[0]:.3f} m ({extent[0]*100:.1f} cm)")
    print(f"    Y = {extent[1]:.3f} m ({extent[1]*100:.1f} cm)")
    print(f"    Z = {extent[2]:.3f} m ({extent[2]*100:.1f} cm)")

    if max_dim < 1.0:
        print("\n" + "!" * 60)
        print(f" WARNUNG: Die maximale Ausdehnung ({max_dim:.3f} m / {max_dim*100:.1f} cm) ist kleiner als 1 Meter!")
        print(" Möglicher Einheitenfehler (z. B. mm statt m beim Export aus Blender/E57).")
        print("!" * 60)
        
        print("\nSoll die Punktwolke skaliert werden?")
        print(" [j] Skaliere um Faktor 1000 (mm -> Meter)")
        print(" [n] Nicht skalieren (Standard)")
        print(" [Eingabe] Beliebigen Faktor eintippen (z. B. 10, 100, 0.1)")
        choice = input("Deine Wahl: ").strip().lower()

        scale_factor = 1.0
        if choice == 'j':
            scale_factor = 1000.0
        elif choice not in ['n', '']:
            try:
                scale_factor = float(choice)
            except ValueError:
                scale_factor = 1.0

        if scale_factor != 1.0:
            target_list = pcds if isinstance(pcds, list) else [pcds]
            print(f" -> Skaliere {len(target_list)} Punktwolke(n) um Faktor {scale_factor}...")
            for p in target_list:
                p.scale(scale_factor, center=(0, 0, 0))

            new_extent = ref_pcd.get_max_bound() - ref_pcd.get_min_bound()
            print(f" -> Neue Ausdehnung: X={new_extent[0]:.3f} m, Y={new_extent[1]:.3f} m, Z={new_extent[2]:.3f} m")

    return pcds

def save_point_cloud_flexible(pcd, file_path):
    """Speichert Punktwolken (.ply, .e57, .las, .pcd, .pts, .xyz)."""
    ext = os.path.splitext(file_path)[1].lower()
    pts = np.asarray(pcd.points)

    if ext == '.e57':
        ensure_package("pye57")
        import pye57
        try:
            e57 = pye57.E57(file_path, mode='w')
            data = {
                "cartesianX": pts[:, 0],
                "cartesianY": pts[:, 1],
                "cartesianZ": pts[:, 2]
            }
            if pcd.has_colors():
                colors = (np.asarray(pcd.colors) * 255).astype(np.uint8)
                data["colorRed"] = colors[:, 0]
                data["colorGreen"] = colors[:, 1]
                data["colorBlue"] = colors[:, 2]
            e57.write_scan_raw(data)
            e57.close()
        except Exception as e:
            print(f"[FEHLER] Schreiben von .e57 fehlgeschlagen: {e}")

    elif ext in ['.las', '.laz']:
        ensure_package("laspy")
        import laspy
        try:
            header = laspy.LasHeader(point_format=3, version="1.2")
            las = laspy.LasData(header)
            las.x = pts[:, 0]
            las.y = pts[:, 1]
            las.z = pts[:, 2]
            if pcd.has_colors():
                colors = (np.asarray(pcd.colors) * 65535).astype(np.uint16)
                las.red = colors[:, 0]
                las.green = colors[:, 1]
                las.blue = colors[:, 2]
            las.write(file_path)
        except Exception as e:
            print(f"[FEHLER] Schreiben von .las fehlgeschlagen: {e}")

    else:
        o3d.io.write_point_cloud(file_path, pcd)

def check_overlap(source, target_unit, max_dist=0.15):
    """Prüft über Achsen-Bounding-Boxen, ob sich zwei Wolken überschneiden."""
    bbox_target = target_unit.get_axis_aligned_bounding_box()
    min_bound = bbox_target.get_min_bound() - max_dist
    max_bound = bbox_target.get_max_bound() + max_dist
    expanded_bbox = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
    cropped = source.crop(expanded_bbox)
    return len(cropped.points) > 100

def extract_transform_metrics(transformation):
    """Extrahiert Rotationswinkel (in Grad) und Verschiebung Z (in cm)."""
    R = transformation[:3, :3]
    t = transformation[:3, 3]

    trace_val = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    angle_deg = np.degrees(np.arccos(trace_val))

    tx_cm, ty_cm, tz_cm = t[0] * 100.0, t[1] * 100.0, t[2] * 100.0
    t_norm_cm = np.linalg.norm(t) * 100.0

    return angle_deg, tx_cm, ty_cm, tz_cm, t_norm_cm

def process_point_cloud(pcd, subsample_cm, filter_level):
    """Führt Subsampling und Outlier Removal durch."""
    processed = pcd

    if subsample_cm > 0:
        voxel_size_m = subsample_cm / 100.0
        processed = processed.voxel_down_sample(voxel_size=voxel_size_m)

    if filter_level > 0:
        filter_params = {
            1: (20, 3.0),
            2: (20, 2.0),
            3: (30, 1.0)
        }
        nb_neighbors, std_ratio = filter_params.get(filter_level, (20, 2.0))
        processed, _ = processed.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, std_ratio=std_ratio
        )

    return processed

def run_incremental_fine_registration(pcds, files):
    """Richtet Scans inkrementell an einer wachsenden Ziel-Einheit aus."""
    print("\n[Vorschaltung] Starte inkrementelle Fine-Registration an kumulierter Einheit...")
    n_pcds = len(pcds)
    if n_pcds == 0:
        return

    accumulated_unit = pcds[0].voxel_down_sample(voxel_size=0.03)
    
    for i in range(1, n_pcds):
        source = pcds[i]
        file_name = files[i]

        if not check_overlap(source, accumulated_unit, max_dist=0.15):
            print(f" -> Skip '{file_name}': Keine ausreichende Überschneidung mit der Einheit.")
            continue

        source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.10, max_nn=30))
        accumulated_unit.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.10, max_nn=30))

        reg_icp = o3d.pipelines.registration.registration_icp(
            source, accumulated_unit, 0.08, np.identity(4),
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=40)
        )

        T = reg_icp.transformation
        angle_deg, tx, ty, tz, t_norm = extract_transform_metrics(T)

        apply_transform = True
        if angle_deg > 2.0 or abs(tz) > 5.0:
            print(f"\n" + "!" * 60)
            print(f" WARNUNG: Starke Anpassung bei Datei: {file_name}")
            print(f"   - Rotation:           {angle_deg:.2f}°  (Limit: 2.00°)")
            print(f"   - Höhenverschiebung:  {tz:+.2f} cm (Limit: ±5.00 cm)")
            print(f"   - Verschiebung X/Y:   X={tx:+.2f} cm, Y={ty:+.2f} cm (Gesamt: {t_norm:.2f} cm)")
            print("!" * 60)
            
            choice = input(f"Soll die Transformation für '{file_name}' übernommen werden? (j/n, Standard: n): ").strip().lower()
            if choice != 'j':
                print(f" -> Abgelehnt. '{file_name}' bleibt in Originalposition.")
                apply_transform = False
            else:
                print(f" -> Vom Benutzer bestätigt.")
        else:
            print(f" -> Fine-Reg '{file_name}': Rot={angle_deg:.2f}°, Z={tz:+.2f}cm (OK)")

        if apply_transform:
            source.transform(T)
            accumulated_unit += source.voxel_down_sample(voxel_size=0.03)

def run_icp_refinement(source, target, max_distance):
    """Point-to-Plane ICP für das Pose-Graph Netzwerk."""
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=max_distance * 2, max_nn=30))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=max_distance * 2, max_nn=30))

    result = o3d.pipelines.registration.registration_icp(
        source, target, max_distance, np.identity(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=50)
    )
    return result.transformation

def main():
    print("=" * 60)
    print("  OPEN3D: POINTCLOUD PROCESSOR & GLOBAL OPTIMISATION")
    print("=" * 60)
    
    path_input = input("Ordnerpfad ODER Pfad zu einer Einzeldatei eingeben: ").strip().strip("'\"")

    if not path_input or not os.path.exists(path_input):
        print("Fehler: Der angegebene Pfad existiert nicht!")
        input("\nDrücke Enter zum Beenden...")
        sys.exit()

    is_single_file = os.path.isfile(path_input)

    # Abfrage für Subsampling und Filtering
    print("-" * 60)
    subsample_input = input("Subsampling-Distanz in cm (z. B. 5 | 0 oder Enter für aus): ").strip()
    try:
        subsample_cm = float(subsample_input) if subsample_input else 0.0
    except ValueError:
        subsample_cm = 0.0

    print("\nFiltering-Stärke (Statistical Outlier Removal):")
    print(" [0] Aus")
    print(" [1] Leicht")
    print(" [2] Mittel")
    print(" [3] Stark")
    filter_input = input("Wähle Stufe (0-3, Standard 0): ").strip()
    try:
        filter_level = int(filter_input) if filter_input else 0
    except ValueError:
        filter_level = 0

    # Abfrage für Ziel-Dateiformat
    print("\nAusgabe-Dateiformat wählen:")
    print(" [0] Originalformat beibehalten")
    print(" [1] PLY (.ply)")
    print(" [2] E57 (.e57)")
    print(" [3] LAS (.las)")
    print(" [4] PCD (.pcd)")
    print(" [5] PTS (.pts)")
    print(" [6] XYZ (.xyz)")
    format_input = input("Wähle Format (0-6, Standard 0): ").strip()

    format_map = {
        '1': '.ply',
        '2': '.e57',
        '3': '.las',
        '4': '.pcd',
        '5': '.pts',
        '6': '.xyz'
    }
    target_ext = format_map.get(format_input, None)

    # FALL A: EINZELDATEI-VERARBEITUNG
    if is_single_file:
        dir_name, base_name = os.path.split(path_input)
        file_stem, ext = os.path.splitext(base_name)

        print(f"\n[1/2] Lade Einzeldatei: {base_name}...")
        pcd = load_point_cloud_flexible(path_input)

        # Ausdehnung prüfen & ggf. skalieren
        pcd = check_and_scale_extent(pcd, label_name=base_name)

        print(f"\n[2/2] Wende Subsampling ({subsample_cm} cm) und Filtering (Stufe {filter_level}) an...")
        processed_pcd = process_point_cloud(pcd, subsample_cm, filter_level)

        out_ext = target_ext if target_ext else ext
        out_path = os.path.join(dir_name, f"{file_stem}_korrigiert{out_ext}")

        print("-" * 60)
        print(f"Speichere verarbeitete Einzeldatei als:\n -> {out_path}")
        save_point_cloud_flexible(processed_pcd, out_path)
        print("=" * 60)
        input("FERTIG! Drücke Enter zum Beenden...")
        sys.exit()

    # FALL B: ORDNER-VERARBEITUNG (MEHRERE FILES)
    print("-" * 60)
    fine_reg_input = input("Vorab inkrementelle Fine-Registration ausführen? (j/n, Standard: n): ").strip().lower()
    enable_fine_reg = (fine_reg_input == 'j')

    valid_extensions = ('.ply', '.pcd', '.pts', '.xyz', '.e57', '.las', '.laz')
    files = [f for f in os.listdir(path_input) if f.lower().endswith(valid_extensions)]
    files.sort()

    if len(files) < 2:
        print("Es müssen mindestens 2 Punktwolken im Ordner liegen.")
        input("\nDrücke Enter zum Beenden...")
        sys.exit()

    output_folder = os.path.join(path_input, "korrigiert")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"\n[1/4] Lade {len(files)} Punktwolken...")
    pcds = [load_point_cloud_flexible(os.path.join(path_input, f)) for f in files]

    # Ausdehnung an der ersten Datei prüfen & ggf. auf alle anwenden
    pcds = check_and_scale_extent(pcds, label_name=files[0])

    if enable_fine_reg:
        run_incremental_fine_registration(pcds, files)

    print(f"\n[2/4] Wende Subsampling ({subsample_cm} cm) und Filtering (Stufe {filter_level}) an...")
    processed_pcds = [process_point_cloud(p, subsample_cm, filter_level) for p in pcds]

    print("\n[3/4] Baue Pose-Graph auf und starte globale Optimierung...")
    max_icp_dist = max(0.10, (subsample_cm / 100.0) * 2.0) if subsample_cm > 0 else 0.10
    
    pose_graph = o3d.pipelines.registration.PoseGraph()
    n_pcds = len(processed_pcds)

    for _ in range(n_pcds):
        pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(np.identity(4)))

    for source_id in range(n_pcds):
        for target_id in range(source_id + 1, n_pcds):
            if not check_overlap(processed_pcds[source_id], processed_pcds[target_id], max_dist=max_icp_dist):
                continue

            transformation = run_icp_refinement(processed_pcds[source_id], processed_pcds[target_id], max_icp_dist)
            info_matrix = o3d.pipelines.registration.get_information_matrix_from_point_clouds(
                processed_pcds[source_id], processed_pcds[target_id], max_icp_dist, transformation
            )

            uncertain = (target_id != source_id + 1)
            pose_graph.edges.append(
                o3d.pipelines.registration.PoseGraphEdge(
                    source_id, target_id, transformation, info_matrix, uncertain=uncertain
                )
            )

    method = o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt()
    criteria = o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria()
    option = o3d.pipelines.registration.GlobalOptimizationOption(
        max_correspondence_distance=max_icp_dist,
        edge_prune_threshold=0.25,
        reference_node=0
    )
    
    o3d.pipelines.registration.global_optimization(pose_graph, method, criteria, option)

    print("\n[4/4] Wende globale Optimierung an und speichere Ergebnisse...")
    combined_pcd = o3d.geometry.PointCloud()

    for i in range(n_pcds):
        trans = pose_graph.nodes[i].pose
        processed_pcds[i].transform(trans)

        out_name = files[i]
        file_stem, ext = os.path.splitext(out_name)
        out_ext = target_ext if target_ext else ext
        out_path = os.path.join(output_folder, f"{file_stem}{out_ext}")
        
        save_point_cloud_flexible(processed_pcds[i], out_path)
        print(f" -> Speichere: korrigiert/{file_stem}{out_ext}")

        combined_pcd += processed_pcds[i]

    gesamt_ext = target_ext if target_ext else '.ply'
    gesamt_file_path = os.path.join(output_folder, f"Gesamt{gesamt_ext}")
    print("-" * 60)
    print(f"Speichere Gesamt{gesamt_ext}...")
    save_point_cloud_flexible(combined_pcd, gesamt_file_path)

    print("\n" + "=" * 60)
    print(f" FERTIG! Ergebnisse gespeichert unter:\n {output_folder}")
    print("=" * 60)
    input("Drücke Enter zum Beenden...")

if __name__ == "__main__":
    main()
