# /// script
# requires-python = ">=3.12"
# dependencies = ["rdkit"]
# ///
"""Build the shared test molecules from PubChem so every tool gets identical input."""
import json
import urllib.request
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

OUT = Path(__file__).resolve().parents[2] / "evidence/fixtures"
MOLECULES = {"simple": ("caffeine", 2519), "complex": ("paclitaxel", 36314), "threed": ("cholesterol", 5997)}

index = {}
for key, (name, cid) in MOLECULES.items():
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/SMILES,MolecularFormula,InChIKey/JSON"
    prop = json.load(urllib.request.urlopen(url))["PropertyTable"]["Properties"][0]
    mol = Chem.MolFromSmiles(prop["SMILES"])
    assert rdMolDescriptors.CalcMolFormula(mol) == prop["MolecularFormula"], name
    assert Chem.MolToInchiKey(mol) == prop["InChIKey"], name
    smiles = prop["SMILES"]  # PubChem's Kekule form: what a chemist copies, and it leaves ring drawing to each tool.
    (OUT / f"{key}.smi").write_text(smiles + "\n")
    flat = Chem.Mol(mol)
    AllChem.Compute2DCoords(flat)
    flat.SetProp("_Name", name)
    Chem.MolToMolFile(flat, str(OUT / f"{key}.mol"))
    solid = Chem.AddHs(mol)
    AllChem.EmbedMolecule(solid, randomSeed=20261105)
    AllChem.MMFFOptimizeMolecule(solid, maxIters=2000)
    solid.SetProp("_Name", name)
    with Chem.SDWriter(str(OUT / f"{key}-3d.sdf")) as writer:
        writer.write(solid)
    index[key] = {
        "name": name, "pubchemCid": cid, "smiles": smiles, "formula": prop["MolecularFormula"],
        "inchiKey": prop["InChIKey"], "mass": round(Descriptors.MolWt(mol), 2),
        "heavyAtoms": mol.GetNumHeavyAtoms(),
        "stereocenters": len(Chem.FindMolChiralCenters(mol, useLegacyImplementation=False)),
    }
(OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
print(json.dumps(index, indent=1))
