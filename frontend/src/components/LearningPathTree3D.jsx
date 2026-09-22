import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function LearningPathTree3D({
  nodes = [],
  activeNodeId,
  onSelectNode,
  className = ''
}) {
  const mountRef = useRef(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const nodeMeshesRef = useRef([]);
  const animFrameIdRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    // 1. Scene setup
    const completionRate = nodes.filter(n => n.status === 'completed').length / (nodes.length || 1);
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    const startBg = new THREE.Color(0x0b0f19); // Dark void
    const endBg = new THREE.Color(0x1e1b4b); // Deep nebula purple
    const bgColor = startBg.clone().lerp(endBg, completionRate);
    scene.background = bgColor;
    scene.fog = new THREE.FogExp2(bgColor, 0.04);

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 3, 11);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x818cf8, 1.5);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    const pointLight = new THREE.PointLight(0x06b6d4, 2, 20);
    pointLight.position.set(0, 3, 2);
    scene.add(pointLight);

    // 5. Ambient Starfield Particle Constellation
    const starGeo = new THREE.BufferGeometry();
    const starCount = 350;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPos[i] = (Math.random() - 0.5) * 40;
      starPos[i + 1] = (Math.random() - 0.5) * 40;
      starPos[i + 2] = (Math.random() - 0.5) * 40;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0x64748b,
      size: 0.12,
      transparent: true,
      opacity: 0.6
    });
    const starField = new THREE.Points(starGeo, starMat);
    scene.add(starField);

    // 6. Build Nodes & Constellation Lines
    const nodeMeshes = [];
    const nodeMap = new Map();

    nodes.forEach((node) => {
      const coords = node.coordinates || { x: 0, y: 0, z: 0 };
      const group = new THREE.Group();
      group.position.set(coords.x, coords.y, coords.z);
      group.userData = { node };

      let coreColor = 0x64748b;
      let emissiveColor = 0x000000;
      let emissiveIntensity = 0.2;
      let size = 0.55;

      if (node.status === 'completed') {
        coreColor = 0x10b981;
        emissiveColor = 0x10b981;
        emissiveIntensity = 0.6;
        size = 0.6;
      } else if (node.status === 'unlocked') {
        coreColor = 0x06b6d4;
        emissiveColor = 0x06b6d4;
        emissiveIntensity = 0.9;
        size = 0.65;
      } else if (node.difficulty === 'remedial') {
        coreColor = 0xf59e0b;
        emissiveColor = 0xf59e0b;
        emissiveIntensity = 0.8;
      }

      // Core shape
      const isTreasure = node.metadata && node.metadata.is_treasure;
      
      if (isTreasure) {
        coreColor = 0xfacc15; // Golden yellow
        emissiveColor = 0xf59e0b;
        emissiveIntensity = 0.8;
      }

      const coreGeo = isTreasure 
        ? new THREE.OctahedronGeometry(size * 1.1) 
        : new THREE.SphereGeometry(size, 32, 32);
        
      const coreMat = new THREE.MeshStandardMaterial({
        color: coreColor,
        emissive: emissiveColor,
        emissiveIntensity: emissiveIntensity,
        roughness: isTreasure ? 0.1 : 0.2,
        metalness: isTreasure ? 0.9 : 0.5,
        transparent: node.status === 'locked',
        opacity: node.status === 'locked' ? 0.35 : 0.95
      });
      const coreMesh = new THREE.Mesh(coreGeo, coreMat);
      if (isTreasure) coreMesh.name = 'treasureMesh'; // tag it to spin in animation loop
      group.add(coreMesh);

      // Active / Unlocked pulsing beacon ring
      if (node.status === 'unlocked') {
        const ringGeo = new THREE.RingGeometry(0.8, 0.9, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.7
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.name = 'beaconRing';
        group.add(ring);
      }

      // Completed orbiting halo & energy dust
      if (node.status === 'completed') {
        const haloGeo = new THREE.TorusGeometry(0.85, 0.03, 16, 48);
        const haloMat = new THREE.MeshStandardMaterial({
          color: 0xfbbf24,
          emissive: 0xf59e0b,
          emissiveIntensity: 0.5
        });
        const halo = new THREE.Mesh(haloGeo, haloMat);
        halo.rotation.x = Math.PI / 4;
        halo.name = 'haloRing';
        group.add(halo);

        // Golden energy dust particles
        const dustGeo = new THREE.BufferGeometry();
        const dustCount = 40;
        const dustPos = new Float32Array(dustCount * 3);
        const dustVel = [];
        for (let i = 0; i < dustCount; i++) {
          dustPos[i*3] = (Math.random() - 0.5) * 1.5;
          dustPos[i*3+1] = (Math.random() - 0.5) * 1.5;
          dustPos[i*3+2] = (Math.random() - 0.5) * 1.5;
          dustVel.push({
            y: Math.random() * 0.02 + 0.005,
            x: (Math.random() - 0.5) * 0.01
          });
        }
        dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
        const dustMat = new THREE.PointsMaterial({
          color: 0xfbbf24,
          size: 0.08,
          transparent: true,
          opacity: 0.8
        });
        const dust = new THREE.Points(dustGeo, dustMat);
        dust.userData = { velocities: dustVel };
        dust.name = 'energyDust';
        group.add(dust);
      }

      scene.add(group);
      nodeMeshes.push(group);
      nodeMap.set(node.id, group);
    });

    nodeMeshesRef.current = nodeMeshes;

    // 7. Render Prerequisite Connection Lines
    nodes.forEach((node) => {
      const prereqs = node.prerequisites || [];
      const targetMesh = nodeMap.get(node.id);
      if (!targetMesh) return;

      prereqs.forEach((prereqId) => {
        const sourceMesh = nodeMap.get(prereqId);
        if (!sourceMesh) return;

        const points = [];
        points.push(sourceMesh.position.clone());
        // Curve midpoint slightly outwards in Z
        const mid = sourceMesh.position.clone().lerp(targetMesh.position, 0.5);
        mid.z += 0.3;
        points.push(mid);
        points.push(targetMesh.position.clone());

        const curve = new THREE.QuadraticBezierCurve3(points[0], points[1], points[2]);
        const curvePoints = curve.getPoints(24);
        const lineGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);

        const isLineActive = node.status !== 'locked';
        const lineMat = new THREE.LineBasicMaterial({
          color: isLineActive ? 0x38bdf8 : 0x334155,
          transparent: true,
          opacity: isLineActive ? 0.75 : 0.25,
          linewidth: isLineActive ? 2 : 1
        });

        const line = new THREE.Line(lineGeo, lineMat);
        scene.add(line);
      });
    });

    // 8. Interactive Orbit Controls (Smooth Pointer Drag)
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let rotationVelocityX = 0;
    let rotationVelocityY = 0;

    const onMouseDown = (e) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / width) * 2 - 1;
      const y = -((e.clientY - rect.top) / height) * 2 + 1;

      // Raycast for hover
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(x, y), camera);
      const intersects = raycaster.intersectObjects(nodeMeshes, true);

      if (intersects.length > 0) {
        let parentGroup = intersects[0].object;
        while (parentGroup.parent && parentGroup.parent !== scene) {
          parentGroup = parentGroup.parent;
        }
        if (parentGroup.userData?.node) {
          setHoveredNode(parentGroup.userData.node);
          container.style.cursor = 'pointer';
        }
      } else {
        setHoveredNode(null);
        container.style.cursor = isDragging ? 'grabbing' : 'grab';
      }

      if (isDragging) {
        const deltaX = e.clientX - prevMouseX;
        const deltaY = e.clientY - prevMouseY;
        rotationVelocityY = deltaX * 0.005;
        rotationVelocityX = deltaY * 0.005;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      }
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      camera.position.z = Math.max(5, Math.min(22, camera.position.z + e.deltaY * 0.01));
    };

    const onClick = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / width) * 2 - 1;
      const y = -((e.clientY - rect.top) / height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(x, y), camera);
      const intersects = raycaster.intersectObjects(nodeMeshes, true);

      if (intersects.length > 0) {
        let parentGroup = intersects[0].object;
        while (parentGroup.parent && parentGroup.parent !== scene) {
          parentGroup = parentGroup.parent;
        }
        if (parentGroup.userData?.node && onSelectNode) {
          onSelectNode(parentGroup.userData.node);
        }
      }
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    container.addEventListener('wheel', onWheel, { passive: false });
    container.addEventListener('click', onClick);

    // 9. Render & Animation Loop
    let clock = new THREE.Clock();

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Damped rotation inertia
      if (!isDragging) {
        rotationVelocityX *= 0.92;
        rotationVelocityY *= 0.92;
      }
      scene.rotation.y += rotationVelocityY;
      scene.rotation.x = Math.max(-0.5, Math.min(0.5, scene.rotation.x + rotationVelocityX));

      // Slow idle starfield drift
      starField.rotation.y = time * 0.02;

      // Animate active beacon rings, halos, & dust
      nodeMeshes.forEach((group) => {
        const beacon = group.getObjectByName('beaconRing');
        if (beacon) {
          const scale = 1 + Math.sin(time * 3) * 0.15;
          beacon.scale.set(scale, scale, scale);
          beacon.material.opacity = 0.5 + Math.sin(time * 3) * 0.3;
        }
        const halo = group.getObjectByName('haloRing');
        if (halo) {
          halo.rotation.z += delta * 0.8;
        }
        const dust = group.getObjectByName('energyDust');
        if (dust) {
          const positions = dust.geometry.attributes.position.array;
          const velocities = dust.userData.velocities;
          for (let i = 0; i < velocities.length; i++) {
            positions[i*3+1] += velocities[i].y;
            positions[i*3] += velocities[i].x;
            if (positions[i*3+1] > 1.5) {
              positions[i*3+1] = -1.5;
              positions[i*3] = (Math.random() - 0.5) * 1.5;
            }
          }
          dust.geometry.attributes.position.needsUpdate = true;
          dust.rotation.y -= delta * 0.2;
        }
        const treasure = group.getObjectByName('treasureMesh');
        if (treasure) {
          treasure.rotation.y += delta * 1.5;
          treasure.rotation.z += delta * 0.5;
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    // Resize observer
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      container.removeEventListener('wheel', onWheel);
      container.removeEventListener('click', onClick);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      if (rendererRef.current?.domElement) {
        rendererRef.current.dispose();
      }
    };
  }, [nodes]);

  return (
    <div className={`three-canvas-container ${className}`} style={{ position: 'relative', width: '100%', height: '520px', borderRadius: '16px', overflow: 'hidden' }}>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* Hover Card Overlay */}
      {hoveredNode && (
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            background: 'rgba(15, 23, 42, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            padding: '10px 14px',
            borderRadius: '10px',
            color: '#fff',
            pointerEvents: 'none',
            maxWidth: '300px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            zIndex: 10
          }}
        >
          <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.8px', color: '#94a3b8', fontWeight: 700 }}>
            {hoveredNode.status === 'completed' ? '✅ Completed' : (hoveredNode.status === 'unlocked' ? '⚡ Ready to Study' : '🔒 Locked')}
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px', color: '#f8fafc' }}>
            {hoveredNode.title}
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
            ⏱️ {hoveredNode.estimated_time_minutes} min &bull; {hoveredNode.difficulty}
          </div>
        </div>
      )}

      {/* Controls Overlay Legend */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          display: 'flex',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.7)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '6px 12px',
          borderRadius: '20px',
          fontSize: '11px',
          color: '#94a3b8',
          alignItems: 'center'
        }}
      >
        <span>Drag to rotate</span> &bull; <span>Scroll to zoom</span> &bull; <span>Click node to inspect</span>
      </div>
    </div>
  );
}
