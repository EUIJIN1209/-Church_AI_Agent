"""
설교 데이터를 위한 데이터 저장 유틸리티.
"""
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .config import StorageConfig
from .models import SermonData
from .exceptions import StorageException


class SermonStorage:
    """설교 데이터의 저장을 처리합니다."""

    def __init__(self, output_file: Optional[Path] = None):
        self.output_file = output_file or StorageConfig.DEFAULT_OUTPUT_FILE
        self.backup_file = StorageConfig.BACKUP_FILE

        # 출력 디렉토리가 존재하는지 확인
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def save(self, sermons: List[SermonData], create_backup: bool = True) -> None:
        """
        설교 데이터를 JSON 파일로 저장합니다.

        Args:
            sermons: SermonData 객체의 리스트
            create_backup: 기존 파일의 백업을 생성할지 여부

        Raises:
            StorageException: 저장 작업이 실패한 경우
        """
        try:
            # 파일이 존재하면 백업 생성
            if create_backup and self.output_file.exists():
                self._create_backup()

            # 딕셔너리 형식으로 변환
            data = [sermon.to_dict() for sermon in sermons]

            # 파일에 쓰기
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"\n✓ Data saved to: {self.output_file}")

        except Exception as e:
            raise StorageException(str(self.output_file), str(e))

    def load(self) -> List[SermonData]:
        """
        JSON 파일에서 설교 데이터를 로드합니다.

        Returns:
            SermonData 객체의 리스트

        Raises:
            StorageException: 로드 작업이 실패한 경우
        """
        try:
            if not self.output_file.exists():
                return []

            with open(self.output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 딕셔너리를 SermonData 객체로 변환
            sermons = []
            for item in data:
                sermon = SermonData(**item)
                sermons.append(sermon)

            return sermons

        except Exception as e:
            raise StorageException(str(self.output_file), f"Load failed: {str(e)}")

    def append(self, sermon: SermonData) -> None:
        """
        기존 데이터에 단일 설교를 추가합니다.

        Args:
            sermon: 추가할 SermonData 객체

        Raises:
            StorageException: 추가 작업이 실패한 경우
        """
        try:
            # 기존 데이터 로드
            sermons = self.load()

            # 중복 확인
            existing_seqs = {s.seq for s in sermons}
            if sermon.seq in existing_seqs:
                print(f"  Warning: Sermon seq={sermon.seq} already exists, skipping")
                return

            # 새 설교 추가
            sermons.append(sermon)

            # 업데이트된 데이터 저장
            self.save(sermons, create_backup=False)

        except Exception as e:
            raise StorageException(str(self.output_file), f"Append failed: {str(e)}")

    def _create_backup(self) -> None:
        """현재 출력 파일의 백업을 생성합니다."""
        try:
            if not self.output_file.exists():
                return

            # 백업 파일명에 타임스탬프 추가
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_file.parent / f"{self.backup_file.stem}_{timestamp}.json"

            # 파일 복사
            with open(self.output_file, "r", encoding="utf-8") as f:
                data = f.read()

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(data)

            print(f"✓ Backup created: {backup_path}")

        except Exception as e:
            print(f"⚠ Backup failed: {e}")

    def file_exists(self) -> bool:
        """출력 파일이 존재하는지 확인합니다."""
        return self.output_file.exists()

    def get_file_path(self) -> Path:
        """출력 파일 경로를 가져옵니다."""
        return self.output_file
