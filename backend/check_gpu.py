#!/usr/bin/env python3
"""
Comprehensive GPU Detection and Compatibility Check
Run this script to check if GPU acceleration is available for your aptamer prediction system.
"""

import sys
import subprocess
import importlib
import platform

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def check_system_info():
    """Check basic system information."""
    print("🖥️  SYSTEM INFORMATION")
    print("=" * 50)
    print(f"Platform: {platform.platform()}")
    print(f"Python Version: {sys.version}")
    print(f"Architecture: {platform.architecture()}")
    print()

def check_nvidia_gpu():
    """Check for NVIDIA GPUs using nvidia-smi."""
    print("🟢 NVIDIA GPU DETECTION")
    print("=" * 50)
    
    # Check if nvidia-smi is available
    stdout, stderr, returncode = run_command("nvidia-smi --version")
    
    if returncode == 0:
        print("✅ NVIDIA drivers installed!")
        print(f"Driver version info:\n{stdout}")
        print()
        
        # Get detailed GPU information
        stdout, stderr, returncode = run_command("nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader,nounits")
        
        if returncode == 0:
            print("🎯 Available NVIDIA GPUs:")
            lines = stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    name, memory, compute_cap = [x.strip() for x in line.split(',')]
                    print(f"  GPU {i}: {name}")
                    print(f"    Memory: {memory} MB")
                    print(f"    Compute Capability: {compute_cap}")
            print()
            
            # Check GPU utilization
            stdout, stderr, returncode = run_command("nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits")
            if returncode == 0:
                print("📊 Current GPU Status:")
                lines = stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        gpu_util, mem_used, mem_total = [x.strip() for x in line.split(',')]
                        print(f"  GPU {i}: {gpu_util}% utilization, {mem_used}/{mem_total} MB memory used")
                print()
        else:
            print("⚠️  Could not get detailed GPU information")
            print(f"Error: {stderr}")
    else:
        print("❌ NVIDIA drivers not found or nvidia-smi not available")
        print("   This doesn't necessarily mean no GPU - check other methods below")
        print()

def check_cuda_availability():
    """Check CUDA availability and version."""
    print("🔥 CUDA AVAILABILITY")
    print("=" * 50)
    
    # Check CUDA compiler
    stdout, stderr, returncode = run_command("nvcc --version")
    if returncode == 0:
        print("✅ CUDA Toolkit installed!")
        lines = stdout.split('\n')
        for line in lines:
            if 'release' in line.lower():
                print(f"CUDA Version: {line.strip()}")
        print()
    else:
        print("❌ CUDA Toolkit not found (nvcc not available)")
        print("   Note: CUDA runtime might still be available for pre-compiled libraries")
        print()

def check_python_gpu_libraries():
    """Check Python libraries for GPU support."""
    print("🐍 PYTHON GPU LIBRARY SUPPORT")
    print("=" * 50)
    
    libraries_to_check = [
        ("torch", "PyTorch"),
        ("tensorflow", "TensorFlow"), 
        ("cupy", "CuPy"),
        ("numba", "Numba"),
        ("xgboost", "XGBoost")
    ]
    
    for lib_name, display_name in libraries_to_check:
        try:
            lib = importlib.import_module(lib_name)
            print(f"✅ {display_name} installed (version: {getattr(lib, '__version__', 'unknown')})")
            
            # Check GPU support for each library
            if lib_name == "torch":
                check_pytorch_gpu(lib)
            elif lib_name == "tensorflow":
                check_tensorflow_gpu(lib)
            elif lib_name == "cupy":
                check_cupy_gpu(lib)
            elif lib_name == "numba":
                check_numba_gpu(lib)
            elif lib_name == "xgboost":
                check_xgboost_gpu(lib)
                
        except ImportError:
            print(f"❌ {display_name} not installed")
    
    print()

def check_pytorch_gpu(torch):
    """Check PyTorch GPU support."""
    try:
        cuda_available = torch.cuda.is_available()
        print(f"   CUDA available: {cuda_available}")
        
        if cuda_available:
            gpu_count = torch.cuda.device_count()
            print(f"   GPU count: {gpu_count}")
            
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
                print(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
                
            # Test GPU operation
            try:
                x = torch.tensor([1.0]).cuda()
                print(f"   ✅ GPU tensor operations working")
            except Exception as e:
                print(f"   ❌ GPU tensor operations failed: {e}")
        
    except Exception as e:
        print(f"   Error checking PyTorch GPU: {e}")

def check_tensorflow_gpu(tf):
    """Check TensorFlow GPU support."""
    try:
        # TensorFlow 2.x
        if hasattr(tf.config, 'list_physical_devices'):
            gpus = tf.config.list_physical_devices('GPU')
            print(f"   GPU devices found: {len(gpus)}")
            
            for i, gpu in enumerate(gpus):
                print(f"   GPU {i}: {gpu}")
                
            if gpus:
                print(f"   ✅ TensorFlow GPU support available")
            else:
                print(f"   ❌ No TensorFlow GPU devices found")
        else:
            # TensorFlow 1.x (legacy)
            print(f"   Legacy TensorFlow version detected")
            
    except Exception as e:
        print(f"   Error checking TensorFlow GPU: {e}")

def check_cupy_gpu(cupy):
    """Check CuPy GPU support."""
    try:
        # Test CuPy GPU operations
        x = cupy.array([1, 2, 3])
        y = cupy.sum(x)
        print(f"   ✅ CuPy GPU operations working")
        
        # Get device info
        device = cupy.cuda.Device()
        print(f"   Current device: {device.id}")
        meminfo = cupy.get_default_memory_pool().used_bytes()
        print(f"   GPU memory pool: {meminfo} bytes used")
        
    except Exception as e:
        print(f"   ❌ CuPy GPU operations failed: {e}")

def check_numba_gpu(numba):
    """Check Numba CUDA support."""
    try:
        from numba import cuda
        
        if cuda.is_available():
            print(f"   ✅ Numba CUDA support available")
            
            # Get device info
            devices = cuda.list_devices()
            print(f"   CUDA devices: {len(devices)}")
            
            for device in devices:
                print(f"   Device: {device}")
                
        else:
            print(f"   ❌ Numba CUDA support not available")
            
    except ImportError:
        print(f"   Numba CUDA module not available")
    except Exception as e:
        print(f"   Error checking Numba CUDA: {e}")

def check_xgboost_gpu(xgb):
    """Check XGBoost GPU support - IMPORTANT for your aptamer prediction system!"""
    try:
        # Create a simple test to see if GPU training works
        import numpy as np
        
        # Generate sample data
        X = np.random.randn(100, 10)
        y = np.random.randint(0, 2, 100)
        
        # Try to create GPU-enabled model
        try:
            model = xgb.XGBClassifier(tree_method='gpu_hist', gpu_id=0)
            model.fit(X, y)
            print(f"   ✅ XGBoost GPU training working!")
            print(f"   🎯 YOUR APTAMER PREDICTION CAN USE GPU ACCELERATION!")
            
        except Exception as gpu_error:
            print(f"   ❌ XGBoost GPU training failed: {gpu_error}")
            
            # Try CPU version to confirm XGBoost works
            try:
                model = xgb.XGBClassifier(tree_method='hist')
                model.fit(X, y)
                print(f"   ✅ XGBoost CPU training working (GPU not available)")
            except Exception as cpu_error:
                print(f"   ❌ XGBoost CPU training also failed: {cpu_error}")
                
    except Exception as e:
        print(f"   Error testing XGBoost: {e}")

def check_other_gpus():
    """Check for other GPU types (AMD, Intel, etc.)."""
    print("🔍 OTHER GPU DETECTION")
    print("=" * 50)
    
    # Check for AMD GPUs
    stdout, stderr, returncode = run_command("rocm-smi --showproductname")
    if returncode == 0:
        print("✅ AMD ROCm GPU detected!")
        print(stdout)
    else:
        print("❌ No AMD ROCm GPUs found")
    
    # Check for Intel GPUs (Linux)
    stdout, stderr, returncode = run_command("intel_gpu_top -l")
    if returncode == 0:
        print("✅ Intel GPU detected!")
    else:
        print("❌ No Intel GPUs found or intel_gpu_top not available")
    
    # General GPU detection via lspci (Linux)
    stdout, stderr, returncode = run_command("lspci | grep -i vga")
    if returncode == 0:
        print("\n📋 All Graphics Devices (lspci):")
        print(stdout)
    
    print()

def provide_recommendations():
    """Provide recommendations based on findings."""
    print("💡 RECOMMENDATIONS FOR YOUR APTAMER PREDICTION SYSTEM")
    print("=" * 60)
    
    print("Based on the above results:")
    print()
    
    print("🎯 For XGBoost GPU Acceleration:")
    print("  • If XGBoost GPU training worked: You're ready to use GPU acceleration!")
    print("  • If failed: Install CUDA-enabled XGBoost or use CPU optimization")
    print()
    
    print("⚡ For Numba GPU Acceleration (k-mer generation):")
    print("  • If Numba CUDA available: Can implement GPU k-mer computation")
    print("  • If not available: Stick with CPU Numba JIT optimization")
    print()
    
    print("🔧 Next Steps:")
    print("  1. If GPU available: Implement tree_method='gpu_hist' in XGBoost")
    print("  2. Consider Numba CUDA for k-mer generation if available")
    print("  3. If no GPU: Focus on CPU optimizations (Numba JIT, more cores)")
    print()
    
    print("📊 Performance Impact:")
    print("  • XGBoost GPU: 2-5x speedup for ML predictions")
    print("  • Numba GPU: 5-20x speedup for k-mer generation")
    print("  • Combined: Potential 10-100x additional speedup")

def main():
    """Main function to run all GPU checks."""
    print("🚀 GPU DETECTION AND COMPATIBILITY CHECK")
    print("=" * 60)
    print("Checking GPU availability for aptamer prediction acceleration...")
    print()
    
    try:
        check_system_info()
        check_nvidia_gpu()
        check_cuda_availability()
        check_python_gpu_libraries()
        check_other_gpus()
        provide_recommendations()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Check interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error during GPU check: {e}")
    
    print("\n" + "=" * 60)
    print("GPU detection complete! Use the information above to determine")
    print("if GPU acceleration is available for your aptamer prediction system.")

if __name__ == "__main__":
    main()