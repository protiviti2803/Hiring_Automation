import sys
import os

# Explicitly ensure pywin32 system DLLs are in the DLL search path on Windows
pywin32_system32 = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages\pywin32_system32")
if os.path.exists(pywin32_system32) and hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(pywin32_system32)
    except Exception:
        pass

# Explicitly ensure paths to installed package libraries are in search path
user_site_path = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages")
win32_path = os.path.join(user_site_path, "win32")
win32_lib_path = os.path.join(user_site_path, "win32", "lib")
for p in [user_site_path, win32_path, win32_lib_path]:
    if p not in sys.path:
        sys.path.append(p)

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_pptx.py <pptx_path> <pdf_path>")
        sys.exit(1)
        
    pptx_path = os.path.abspath(sys.argv[1])
    pdf_path = os.path.abspath(sys.argv[2])
    
    if sys.platform.startswith("win"):
        # Import COM libraries inside the separate process context
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        try:
            powerpoint = win32com.client.DispatchEx("Powerpoint.Application")
            try:
                # Open template. WithWindow=False runs it invisibly in the background
                deck = powerpoint.Presentations.Open(pptx_path, WithWindow=False)
            except Exception:
                # Fallback if window rendering context is required
                deck = powerpoint.Presentations.Open(pptx_path, WithWindow=True)
                
            # 32 is the code for saving as PDF in PowerPoint COM
            deck.SaveAs(pdf_path, 32)
            deck.Close()
            powerpoint.Quit()
            print("Successfully converted PPTX to PDF via PowerPoint COM.")
        except Exception as e:
            print(f"Error during PowerPoint COM conversion: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            pythoncom.CoUninitialize()
    else:
        # On Linux, invoke headless LibreOffice
        output_dir = os.path.dirname(pdf_path)
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            pptx_path
        ]
        import subprocess
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Align output filename with expectations
            base_name = os.path.splitext(os.path.basename(pptx_path))[0]
            generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
            if os.path.exists(generated_pdf) and generated_pdf != pdf_path:
                os.replace(generated_pdf, pdf_path)
            print("Successfully converted PPTX to PDF via LibreOffice.")
        except Exception as e:
            print(f"Error during LibreOffice conversion: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
