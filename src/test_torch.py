import torch

def check_torch_device():
    print("\n===== PYTORCH DEVICE INFO =====")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name()}")
        print(f"Device count: {torch.cuda.device_count()}")
        device = torch.device("cuda")
    else:
        print("Using CPU only")
        device = torch.device("cpu")
    
    print(f"Active device: {device}")
    
    # Create a test tensor to verify
    x = torch.randn(3,3)
    print(f"\nTest tensor device: {x.device}")

if __name__ == "__main__":
    check_torch_device()
