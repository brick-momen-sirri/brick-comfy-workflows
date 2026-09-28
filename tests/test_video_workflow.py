"""Offline regression checks for video validation and LTX frame handling.

Run: python -m unittest discover -s tests -v
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate_workflows.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class VideoValidationTests(unittest.TestCase):
    def test_saved_video_is_an_output_but_caption_and_preview_are_not(self):
        info = {"VHS_VideoCombine": {"output_node": True}, "AILab_QwenVL_GGUF": {"output_node": True}}
        api = {"1": {"class_type": "VHS_VideoCombine", "inputs": {"save_output": True}},
               "2": {"class_type": "AILab_QwenVL_GGUF", "inputs": {}}}
        check = validator.Checker(api, info)
        self.assertTrue(check.has_saved_output(check.executed({})[0]))
        api["1"]["inputs"]["save_output"] = False
        self.assertFalse(check.has_saved_output(check.executed({})[0]))
        del api["1"]
        self.assertFalse(check.has_saved_output(check.executed({})[0]))

    def test_legacy_and_v3_combos_report_missing_files_and_invalid_choices(self):
        for kind, opts in [(["present.safetensors"], {}), ("COMBO", {"options": ["present.safetensors"]})]:
            check = validator.Checker({}, {})
            check.check_value("loader", "model", "missing.safetensors", kind, opts)
            self.assertEqual(len(check.warnings), 1)
            self.assertFalse(check.errors)
        check = validator.Checker({}, {})
        check.check_value("video", "video", "input.mp4", [], {})
        self.assertEqual(len(check.warnings), 1)
        check.check_value("sampler", "sampler", "typo", "COMBO", {"options": ["euler"]})
        self.assertEqual(len(check.errors), 1)

    def test_autogrow_inputs_require_a_valid_child_and_validate_its_type(self):
        info = {
            "Math": {"input": {"required": {
                "expression": ["STRING"],
                "values": ["COMFY_AUTOGROW_V3", {"template": {
                    "input": {"required": {"value": ["FLOAT,INT,BOOLEAN", {}]}},
                    "names": ["a", "b"], "min": 1}}]}}, "output": ["INT"]},
            "Source": {"input": {"required": {}}, "output": ["INT"]}}
        api = {"1": {"class_type": "Source", "inputs": {}},
               "2": {"class_type": "Math", "inputs": {"expression": "a", "values.a": ["1", 0]}}}
        check = validator.Checker(api, info)
        check.check()
        self.assertFalse(check.errors + check.warnings)
        wrong = copy.deepcopy(info)
        wrong["Source"]["output"] = ["IMAGE"]
        check = validator.Checker(api, wrong)
        check.check()
        self.assertTrue(any("cannot feed" in error for error in check.errors))
        del api["2"]["inputs"]["values.a"]
        check = validator.Checker(api, info)
        check.check()
        self.assertTrue(any("autogrow" in error for error in check.errors))

    def test_format_specific_video_options_are_checked(self):
        info = {"Video": {"input": {"required": {"format": [["video/h264-mp4"], {
            "formats": {"video/h264-mp4": [["crf", "INT", {"min": 0, "max": 100}],
                                           ["pix_fmt", ["yuv420p", "yuv420p10le"]]]}}]}}, "output": []}}
        api = {"1": {"class_type": "Video", "inputs": {"format": "video/h264-mp4", "crf": 101, "pix_fmt": "typo"}}}
        check = validator.Checker(api, info)
        check.check()
        self.assertEqual(len(check.errors), 2)
        self.assertFalse(check.warnings)


class LTXGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = json.loads((ROOT / "workflows/ltx25-video-upscale/ltx25_video_upscale.api.json").read_text(encoding="utf-8"))

    def test_all_frame_counts_pad_to_ltx_alignment_and_trim_without_loss(self):
        expression = self.api["63"]["inputs"]["expression"]
        for count in range(1, 4097):
            padding = eval(expression, {"__builtins__": {}}, {"a": count})
            self.assertGreaterEqual(padding, 1)  # KJ repeat node minimum
            self.assertLessEqual(padding, 8)
            self.assertEqual((count + padding) % 8, 1)
            frames = list(range(count))
            self.assertEqual((frames + [frames[-1]] * padding)[:count], frames)
        self.assertEqual(self.api["70"]["inputs"]["num_frames"], ["29", 1])
        self.assertEqual(self.api["70"]["inputs"]["start_index"], 0)

    def test_default_frame_rates_and_audio_route_agree(self):
        self.assertEqual(self.api["29"]["inputs"]["force_rate"], self.api["40"]["inputs"]["frame_rate"])
        self.assertEqual(self.api["10"]["inputs"]["frame_rate"], self.api["40"]["inputs"]["frame_rate"])
        self.assertEqual(self.api["40"]["inputs"]["audio"], ["29", 2])
        self.assertEqual(self.api["29"]["inputs"]["skip_first_frames"], 0)


if __name__ == "__main__":
    unittest.main()
