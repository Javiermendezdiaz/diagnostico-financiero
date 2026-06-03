#!/usr/bin/env python3
"""
Production Deployment — Diagnóstico Financiero 3-Fase
Ejecuta git commands desde Windows native path
"""

import subprocess
import sys
import os

# Windows native path (no WSL translation)
deploy_dir = r"C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

def run_command(cmd, description):
    """Execute command and report status"""
    print(f"\n[*] {description}...")
    try:
        result = subprocess.run(cmd, cwd=deploy_dir, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"    ✓ {description} OK")
            if result.stdout:
                print(f"    {result.stdout[:200]}")
            return True
        else:
            print(f"    ✗ ERROR: {description}")
            print(f"    {result.stderr}")
            return False
    except Exception as e:
        print(f"    ✗ EXCEPTION: {e}")
        return False

def main():
    print("=" * 70)
    print("DEPLOYMENT: Diagnóstico Financiero 3-Fase → GitHub + Railway")
    print("=" * 70)
    
    # Step 1: Verify git repo
    print(f"\n[Setup] Working directory: {deploy_dir}")
    print(f"[Setup] Checking git repository...")
    
    git_check = subprocess.run(
        "git rev-parse --git-dir", 
        cwd=deploy_dir, 
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    if git_check.returncode != 0:
        print("✗ FATAL: Not a git repository")
        print(f"  {git_check.stderr}")
        sys.exit(1)
    
    print(f"✓ Git repository detected")
    
    # Step 2-4: Deploy
    steps = [
        ("git add .", "Adding files"),
        ("git commit -m 'Ready for production'", "Committing"),
        ("git push origin main", "Pushing to GitHub"),
    ]
    
    all_passed = True
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            all_passed = False
            break
    
    # Report
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ DEPLOYMENT SUCCESSFUL")
        print("\nNext steps:")
        print("  1. Go to railway.app")
        print("  2. New Project > GitHub > diagnostico-financiero")
        print("  3. Railway auto-deploys on push (detects Python/FastAPI)")
        print("\nSystem ready for production. 🚀")
        return 0
    else:
        print("✗ DEPLOYMENT FAILED")
        print("Check git config, GitHub credentials, and network connectivity")
        return 1

if __name__ == "__main__":
    sys.exit(main())
