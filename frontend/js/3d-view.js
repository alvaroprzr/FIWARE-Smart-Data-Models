// TODO: render the 3D city scene with station towers and topographic context.

export function initialize3DView(containerId = 'three-view') {
  const container = document.getElementById(containerId);
  if (!container || typeof window.THREE === 'undefined') {
    return null;
  }

  const scene = new window.THREE.Scene();
  scene.background = new window.THREE.Color(0x09131f);

  const camera = new window.THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
  camera.position.set(0, 8, 14);

  const renderer = new window.THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  const geometry = new window.THREE.BoxGeometry(2, 2, 2);
  const material = new window.THREE.MeshStandardMaterial({ color: 0x30d5c8 });
  const cube = new window.THREE.Mesh(geometry, material);
  scene.add(cube);

  const light = new window.THREE.DirectionalLight(0xffffff, 1.2);
  light.position.set(5, 10, 7);
  scene.add(light);

  const ambient = new window.THREE.AmbientLight(0xffffff, 0.5);
  scene.add(ambient);

  const animate = () => {
    cube.rotation.x += 0.01;
    cube.rotation.y += 0.013;
    renderer.render(scene, camera);
    window.requestAnimationFrame(animate);
  };

  animate();
  return { scene, camera, renderer };
}