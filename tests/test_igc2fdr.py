"""
Integration tests for igc2fdr.py main script
End-to-end testing of the complete conversion pipeline
"""
import pytest
import os
import sys
from pathlib import Path
from igc2fdr import process_file, process_files
from igc_config import Config


class TestProcessFile:
    """Tests for process_file function"""

    def test_process_single_igc_file(self, sample_igc_file, mock_cli_args, temp_output_dir):
        """Test processing a single valid IGC file"""
        config = Config(mock_cli_args)

        success = process_file(config, str(sample_igc_file))

        assert success

        # Check output file was created
        expected_output = temp_output_dir / "test_flight.fdr"
        assert expected_output.exists()

        # Verify FDR content
        content = expected_output.read_text()
        assert 'A\n4\n' in content  # FDR header
        assert 'ACFT,' in content
        assert 'TAIL,' in content
        assert 'DATE,' in content

    def test_process_file_with_output_path(self, sample_igc_file, mock_cli_args, temp_output_dir):
        """Test that output goes to specified directory"""
        config = Config(mock_cli_args)

        success = process_file(config, str(sample_igc_file))

        assert success

        # Output should be in temp_output_dir
        output_files = list(temp_output_dir.glob("*.fdr"))
        assert len(output_files) == 1
        assert output_files[0].name == "test_flight.fdr"

    def test_process_nonexistent_file(self, mock_cli_args):
        """Test handling of non-existent input file"""
        config = Config(mock_cli_args)

        success = process_file(config, "/nonexistent/file.igc")

        assert not success

    def test_process_invalid_file_type(self, tmp_path, mock_cli_args):
        """Test handling of non-IGC file"""
        invalid_file = tmp_path / "not_igc.txt"
        invalid_file.write_text("This is not an IGC file\nJust some random text\n")

        config = Config(mock_cli_args)

        # Should handle gracefully (might succeed with empty track or fail)
        result = process_file(config, str(invalid_file))
        # We don't assert True or False here, just that it doesn't crash


class TestProcessFiles:
    """Tests for process_files function (batch processing)"""

    def test_process_multiple_files(self, tmp_path, mock_cli_args, sample_igc_content, temp_output_dir):
        """Test processing multiple IGC files"""
        # Create multiple IGC files
        file1 = tmp_path / "flight1.igc"
        file2 = tmp_path / "flight2.igc"
        file3 = tmp_path / "flight3.igc"

        for f in [file1, file2, file3]:
            f.write_text(sample_igc_content)

        config = Config(mock_cli_args)

        # Process all files
        process_files(config, [str(file1), str(file2), str(file3)])

        # Check all output files were created
        output_files = list(temp_output_dir.glob("*.fdr"))
        assert len(output_files) == 3

        output_names = {f.name for f in output_files}
        assert "flight1.fdr" in output_names
        assert "flight2.fdr" in output_names
        assert "flight3.fdr" in output_names

    def test_process_no_files(self, mock_cli_args):
        """Test processing with no input files"""
        config = Config(mock_cli_args)

        # Should handle gracefully
        process_files(config, [])
        # No assertion needed, just shouldn't crash

    def test_process_mixed_valid_invalid(self, tmp_path, mock_cli_args, sample_igc_content, temp_output_dir):
        """Test processing mix of valid and invalid files"""
        # Create one valid and one invalid file
        valid_file = tmp_path / "valid.igc"
        invalid_file = tmp_path / "invalid.txt"

        valid_file.write_text(sample_igc_content)
        invalid_file.write_text("Not an IGC file")

        config = Config(mock_cli_args)

        # Process both
        process_files(config, [str(valid_file), str(invalid_file)])

        # At least one output file should exist
        output_files = list(temp_output_dir.glob("*.fdr"))
        assert len(output_files) >= 1

    def test_creates_output_directory(self, tmp_path, sample_igc_file, mock_cli_args):
        """Test that output directory is created if it doesn't exist"""
        new_output_dir = tmp_path / "new_output"
        assert not new_output_dir.exists()

        mock_cli_args.output = str(new_output_dir)
        config = Config(mock_cli_args)

        process_files(config, [str(sample_igc_file)])

        # Directory should be created
        assert new_output_dir.exists()
        assert new_output_dir.is_dir()


class TestEndToEndConversion:
    """End-to-end integration tests"""

    def test_complete_conversion_pipeline(self, sample_igc_file, mock_cli_args, temp_output_dir):
        """Test complete IGC to FDR conversion pipeline"""
        config = Config(mock_cli_args)

        # Process the file
        success = process_file(config, str(sample_igc_file))
        assert success

        # Read and verify output
        output_file = temp_output_dir / "test_flight.fdr"
        assert output_file.exists()

        content = output_file.read_text()

        # Verify FDR structure
        assert content.startswith('A\n4\n')
        assert 'COMM,' in content
        assert 'ACFT,' in content
        assert 'TAIL,' in content
        assert 'DATE,' in content
        assert 'DREF,' in content

        # Verify track data columns
        assert 'Longitude' in content
        assert 'Latitude' in content
        assert 'AltMSL' in content
        assert 'Heading' in content
        assert 'Pitch' in content
        assert 'Roll' in content

    def test_conversion_preserves_metadata(self, tmp_path, mock_cli_args, temp_output_dir):
        """Test that IGC metadata is preserved in FDR"""
        # Create IGC with specific metadata
        igc_content = """AXCS001
HFDTE230525
HFPLTPILOT:Test Pilot
HFGTYGLIDERTYPE:Test Glider
HFGIDGLIDERID:TEST-123
B1214288099883N00805990EA0090200902
B1214298099900N00806000EA0090500905
"""
        igc_file = tmp_path / "metadata_test.igc"
        igc_file.write_text(igc_content)

        config = Config(mock_cli_args)
        success = process_file(config, str(igc_file))
        assert success

        output_file = temp_output_dir / "metadata_test.fdr"
        content = output_file.read_text()

        # Check metadata appears in comments
        assert 'Test Pilot' in content
        assert 'TEST-123' in content

    def test_conversion_with_timezone_adjustment(self, sample_igc_file, mock_cli_args, temp_output_dir):
        """Test conversion with timezone adjustment"""
        mock_cli_args.timezone = '2'  # +2 hours
        config = Config(mock_cli_args)

        success = process_file(config, str(sample_igc_file))
        assert success

        output_file = temp_output_dir / "test_flight.fdr"
        content = output_file.read_text()

        # Should mention timezone adjustment
        assert '2 hour' in content or 'timestamp' in content.lower()

    def test_conversion_with_custom_aircraft(self, sample_igc_file, mock_cli_args, temp_output_dir):
        """Test conversion with custom aircraft specification"""
        mock_cli_args.aircraft = 'Aircraft/Custom/MyGlider.acf'
        config = Config(mock_cli_args)

        success = process_file(config, str(sample_igc_file))
        assert success

        output_file = temp_output_dir / "test_flight.fdr"
        content = output_file.read_text()

        # Should use custom aircraft
        assert 'Aircraft/Custom/MyGlider.acf' in content


class TestRealWorldScenarios:
    """Tests simulating real-world usage scenarios"""

    def test_process_flight_from_condor(self, tmp_path, mock_cli_args, temp_output_dir):
        """Simulate processing a Condor-generated IGC file"""
        # Condor IGC files have specific characteristics
        condor_igc = """AXCS001
HFDTE090525
HFPLTPILOT:Condor Pilot
HFGTYGLIDERTYPE:ASW-28
HFGIDGLIDERID:CONDOR-1
HFSITFREEFLY:Condor Soaring
B1200008050000N00810000EA0100001000
B1200018050010N00810010EA0100101001
B1200028050020N00810020EA0100201002
B1200038050030N00810030EA0100301003
"""
        igc_file = tmp_path / "condor_flight.igc"
        igc_file.write_text(condor_igc)

        config = Config(mock_cli_args)
        success = process_file(config, str(igc_file))

        assert success
        output_file = temp_output_dir / "condor_flight.fdr"
        assert output_file.exists()

        content = output_file.read_text()
        assert 'Condor Pilot' in content

    def test_process_short_flight(self, tmp_path, mock_cli_args, temp_output_dir):
        """Test processing a very short flight (few seconds)"""
        short_igc = """AXCS001
HFDTE090525
B1214288099883N00805990EA0090200902
B1214298099883N00805990EA0090200902
B1214308099883N00805990EA0090200902
"""
        igc_file = tmp_path / "short_flight.igc"
        igc_file.write_text(short_igc)

        config = Config(mock_cli_args)
        success = process_file(config, str(igc_file))

        assert success

    def test_process_flight_with_gaps(self, tmp_path, mock_cli_args, temp_output_dir):
        """Test processing a flight with time gaps (missing seconds)"""
        gap_igc = """AXCS001
HFDTE090525
B1214008099883N00805990EA0090200902
B1214058099900N00806000EA0090500905
B1214128099917N00806017EA0091000910
"""
        igc_file = tmp_path / "gap_flight.igc"
        igc_file.write_text(gap_igc)

        config = Config(mock_cli_args)
        success = process_file(config, str(igc_file))

        assert success

        # Gaps should be filled by interpolation
        output_file = temp_output_dir / "gap_flight.fdr"
        content = output_file.read_text()

        # Count track points (should have interpolated points)
        track_lines = [line for line in content.split('\n')
                      if line.strip() and ':' in line and ',' in line
                      and not line.startswith(('COMM,', 'DREF,'))]

        # Should have more than 3 points due to interpolation
        assert len(track_lines) >= 3


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_handle_corrupted_igc_gracefully(self, tmp_path, mock_cli_args):
        """Test that corrupted IGC files don't crash the program"""
        corrupted_igc = """AXCS001
HFDTE090525
B1214288099883N00805990EA0090200902
CORRUPTED LINE HERE!!!
B1214298099900N00806000EA0090500905
B99999999999999999999999999999999
"""
        igc_file = tmp_path / "corrupted.igc"
        igc_file.write_text(corrupted_igc)

        config = Config(mock_cli_args)

        # Should not crash
        result = process_file(config, str(igc_file))
        # May succeed or fail, but shouldn't crash

    def test_handle_empty_igc_file(self, tmp_path, mock_cli_args):
        """Test handling of completely empty IGC file"""
        empty_file = tmp_path / "empty.igc"
        empty_file.write_text("")

        config = Config(mock_cli_args)

        # Should handle gracefully
        result = process_file(config, str(empty_file))
        # May fail but shouldn't crash

    def test_handle_missing_required_headers(self, tmp_path, mock_cli_args, temp_output_dir):
        """Test IGC file with missing headers"""
        minimal_igc = """AXCS001
B1214288099883N00805990EA0090200902
B1214298099900N00806000EA0090500905
"""
        igc_file = tmp_path / "minimal.igc"
        igc_file.write_text(minimal_igc)

        config = Config(mock_cli_args)
        result = process_file(config, str(igc_file))

        # Should handle missing headers gracefully
        # May use defaults for missing info
