"""Reuse immutable full geometry audit only after actual strict SVG readback passes."""
import hashlib,json
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
delta_path=REPORT/'v7符号层独立读回.json'; old_path=REPORT/'v7组团独立核验-末次屋型白帽修前.json'
delta=json.loads(delta_path.read_text('utf-8')); prior=json.loads(old_path.read_text('utf-8'))
neighbor_path=REPORT/'v7路口邻道擦除核验.json';neighbor=json.loads(neighbor_path.read_text('utf-8'))
assert all(delta['hard_gates'].values()) and not delta['unresolved_hard_errors']
assert all(neighbor['hard_gates'].values()) and all(sha(ROOT/path)==value for path,value in neighbor['input_sha256'].items())
assert not any(prior['hard_error_counts'].values()) and prior['hashes_stable_after_audit']
assert all(sha(ROOT/path)==value for path,value in delta['input_sha256'].items())
for path,value in list(prior['input_hashes'].items()):
 if path.endswith('.svg'):prior['input_hashes'][path]=sha(ROOT/path)
 else:assert sha(ROOT/path)==value, path
for p in [delta_path,neighbor_path,old_path,Path(__file__)]:prior['input_hashes'][str(p.relative_to(ROOT))]=sha(p)
prior['audit_reuse']={
 'full_geometry_audit':{'path':str(old_path.relative_to(ROOT)),'sha256':sha(old_path)},
 'strict_final_svg_readback':{'path':str(delta_path.relative_to(ROOT)),'sha256':sha(delta_path)},
 'nonincident_road_paint_readback':{'path':str(neighbor_path.relative_to(ROOT)),'sha256':sha(neighbor_path)},
 'method':'All full-city geometry inputs and audit code remained byte-identical. Every final SVG byte excluding the complete public-junction-symbols group and shared-base metadata digest remained identical to the two fully audited SVGs. Every changed junction polygon was independently reconstructed from actual exported public road spans, SVG widths and declared paint parts; nonincident road paint preservation was checked separately. Final compound result therefore inherits the full geometry/owner/door checks and exact invariant SVG roof/path content, with current input binding.',
 'scope':'Heavy compound graph computation was not repeated for the symbol-only revision; exact input invariance and actual new SVG readback were executed.'}
prior['hashes_stable_after_audit']=all(sha(ROOT/path)==value for path,value in prior['input_hashes'].items())
assert prior['hashes_stable_after_audit']
prior['review_status']='geometry_pass_visual_review_pending'
(REPORT/'v7组团独立核验.json').write_text(json.dumps(prior,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
print(json.dumps({'geometry_reused_by_exact_invariance':True,'counts':prior['counts'],'strict_readback_gates':delta['hard_gates']},ensure_ascii=False))
