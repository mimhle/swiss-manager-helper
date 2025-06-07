# Swiss-Manager helper
This is a helper for [Swiss-Manager](https://swiss-manager.at/), a pairing program for swiss and round-robin tournaments.
### Features
- Generate Swiss-Manager compatible XML files for players and teams.
- Import from Excel.
- Normalize player names and team names for use in Swiss-Manager.
- Mapping for short names to full names for teams.
- Detect duplicate player names.
- Generate player cards (WIP need more testing).
- Calculate team statistics and rankings.
- QR code generator.
### Usage
1. Clone the repository:
```bash
git clone https://github.com/mimhle/swiss-manager-helper
cd swiss-manager-helper
```
2. Install the required packages:
```bash
pip install -r requirements.txt
```
3. Run in development mode:
```bash
python app.py
```